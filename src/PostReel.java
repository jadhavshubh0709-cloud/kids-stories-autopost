import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Publishes today's reel to Instagram via the Instagram API with Instagram Login.
 *
 * Folder convention:  reels/YYYY-MM-DD/reel.mp4  +  reels/YYYY-MM-DD/caption.txt
 * The mp4 must be reachable on a public HTTPS URL (GitHub Pages):  PAGES_BASE_URL/reels/YYYY-MM-DD/reel.mp4
 *
 * Env vars:
 *   IG_ACCESS_TOKEN  never-expiring System User token (instagram_basic + instagram_content_publish)
 *   IG_USER_ID       optional: Instagram account id. If empty, it is looked up from IG_BUSINESS_ID + IG_USERNAME
 *   IG_BUSINESS_ID   business portfolio id (used for the lookup)
 *   IG_USERNAME      Instagram username without @ (used for the lookup)
 *   PAGES_BASE_URL   e.g. https://yourname.github.io/insta-autopost
 *   POST_DATE        optional, YYYY-MM-DD (defaults to today in Asia/Kolkata)
 *   GRAPH_HOST       optional, default graph.facebook.com
 *   GRAPH_VERSION    optional, default v25.0
 *
 * Run (Java 11+):  java src/PostReel.java
 */
public class PostReel {

    private static final HttpClient HTTP = HttpClient.newHttpClient();

    public static void main(String[] args) throws Exception {
        String token = required("IG_ACCESS_TOKEN");
        String base = required("PAGES_BASE_URL").replaceAll("/+$", "");
        String version = env("GRAPH_VERSION", "v25.0");
        String date = env("POST_DATE", LocalDate.now(ZoneId.of("Asia/Kolkata")).toString());
        String api = "https://" + env("GRAPH_HOST", "graph.facebook.com") + "/" + version;
        String igUserId = env("IG_USER_ID", "");
        if (igUserId.isEmpty()) igUserId = lookupIgUserId(api, token);
        System.out.println("Instagram account id: " + igUserId);
        String who = get(api + "/" + igUserId + "?fields=id,username&access_token=" + enc(token));
        System.out.println("Account check: " + who);
        if (env("DRY_RUN", "false").equals("true")) {
            System.out.println("DRY_RUN: token and account OK, nothing posted.");
            return;
        }

        Path dir = Path.of("reels", date);
        Path captionFile = dir.resolve("caption.txt");
        if (!Files.exists(dir.resolve("reel.mp4")) || !Files.exists(captionFile)) {
            System.out.println("No reel scheduled for " + date + " (expected " + dir + "/reel.mp4 + caption.txt). Nothing to do.");
            return;
        }
        String caption = Files.readString(captionFile, StandardCharsets.UTF_8).strip();
        String videoUrl = base + "/reels/" + date + "/reel.mp4";
        System.out.println("Posting reel for " + date + " from " + videoUrl);

        // 1) Create the REELS media container
        Map<String, String> params = new LinkedHashMap<>();
        params.put("media_type", "REELS");
        params.put("video_url", videoUrl);
        params.put("caption", caption);
        params.put("share_to_feed", "true");
        // Cover = the hook screen (first scene) once its text is fully on screen.
        // A custom image can be used instead by adding reels/<date>/cover.jpg.
        if (Files.exists(dir.resolve("cover.jpg"))) {
            params.put("cover_url", base + "/reels/" + date + "/cover.jpg");
        } else {
            params.put("thumb_offset", env("COVER_OFFSET_MS", "2000"));
        }
        params.put("access_token", token);
        String created = post(api + "/" + igUserId + "/media", params);
        String containerId = field(created, "id");
        System.out.println("Container: " + containerId);

        // 2) Wait for Instagram to download + process the video
        String status = "IN_PROGRESS";
        for (int i = 0; i < 40 && !status.equals("FINISHED"); i++) {
            Thread.sleep(15_000);
            String res = get(api + "/" + containerId + "?fields=status_code,status&access_token=" + enc(token));
            status = field(res, "status_code");
            System.out.println("  status: " + status);
            if (status.equals("ERROR") || status.equals("EXPIRED")) {
                throw new IllegalStateException("Container failed: " + res);
            }
        }
        if (!status.equals("FINISHED")) throw new IllegalStateException("Timed out waiting for video processing");

        // 3) Publish
        String published = post(api + "/" + igUserId + "/media_publish",
                Map.of("creation_id", containerId, "access_token", token));
        System.out.println("Published! Media id: " + field(published, "id"));
    }

    /** Finds the Instagram account id owned by the business portfolio, matching IG_USERNAME. */
    private static String lookupIgUserId(String api, String token) throws Exception {
        String biz = required("IG_BUSINESS_ID");
        String username = required("IG_USERNAME").replace("@", "");
        for (String edge : new String[]{"owned_instagram_accounts", "instagram_accounts"}) {
            try {
                String res = get(api + "/" + biz + "/" + edge + "?fields=id,username&access_token=" + enc(token));
                Matcher m = Pattern.compile("\\{[^{}]*\"id\"\\s*:\\s*\"(\\d+)\"[^{}]*\\}").matcher(res);
                String first = null;
                while (m.find()) {
                    if (first == null) first = m.group(1);
                    if (m.group().contains("\"" + username + "\"")) return m.group(1);
                }
                if (first != null) return first;
                System.out.println("  " + edge + ": no accounts in " + res);
            } catch (IllegalStateException e) {
                System.out.println("  " + edge + " lookup failed: " + e.getMessage());
            }
        }
        throw new IllegalStateException("Could not find the Instagram account id. Set the IG_USER_ID secret manually.");
    }

    private static String post(String url, Map<String, String> form) throws Exception {
        String body = form.entrySet().stream()
                .map(e -> enc(e.getKey()) + "=" + enc(e.getValue()))
                .collect(Collectors.joining("&"));
        HttpRequest req = HttpRequest.newBuilder(URI.create(url))
                .header("Content-Type", "application/x-www-form-urlencoded")
                .POST(HttpRequest.BodyPublishers.ofString(body)).build();
        return send(req);
    }

    private static String get(String url) throws Exception {
        return send(HttpRequest.newBuilder(URI.create(url)).GET().build());
    }

    private static String send(HttpRequest req) throws Exception {
        HttpResponse<String> res = HTTP.send(req, HttpResponse.BodyHandlers.ofString());
        if (res.statusCode() >= 400) {
            throw new IllegalStateException("HTTP " + res.statusCode() + ": " + res.body());
        }
        return res.body();
    }

    private static String field(String json, String name) {
        Matcher m = Pattern.compile("\"" + name + "\"\\s*:\\s*\"([^\"]*)\"").matcher(json);
        if (!m.find()) throw new IllegalStateException("Field '" + name + "' not found in: " + json);
        return m.group(1);
    }

    private static String enc(String s) { return URLEncoder.encode(s, StandardCharsets.UTF_8); }

    private static String env(String k, String def) {
        String v = System.getenv(k);
        return (v == null || v.isBlank()) ? def : v.trim();
    }

    private static String required(String k) {
        String v = System.getenv(k);
        if (v == null || v.isBlank()) throw new IllegalStateException("Missing env var " + k);
        return v.trim();
    }
}
