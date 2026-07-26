package de.icekey.inventory;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.GeolocationPermissions;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.ProgressBar;

import androidx.activity.OnBackPressedCallback;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.webkit.WebSettingsCompat;
import androidx.webkit.WebViewFeature;

/** Full-screen WebView shell for the Icekey Inventory PWA. */
public class WebViewActivity extends AppCompatActivity {
    public static final String PREFS_NAME = "icekey_inventory";
    public static final String PREF_SERVER_URL = "server_url";
    public static final String DEFAULT_SERVER_URL = "http://192.168.178.69:18000/m/dashboards/";
    private static final int LOCATION_REQUEST_CODE = 42;

    private WebView webView;
    private ProgressBar progressBar;
    private FrameLayout splashView;
    private String pendingGeoOrigin;
    private GeolocationPermissions.Callback pendingGeoCallback;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().setStatusBarColor(Color.TRANSPARENT);
        getWindow().setNavigationBarColor(ContextCompat.getColor(this, R.color.icekey_dark));

        FrameLayout root = new FrameLayout(this);
        webView = new WebView(this);
        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        splashView = createSplashView();

        root.addView(webView, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        root.addView(progressBar, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(3), Gravity.TOP));
        root.addView(splashView, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(root);

        configureWebView();
        webView.setOnLongClickListener(v -> {
            startActivity(new Intent(this, SettingsActivity.class));
            return true;
        });
        splashView.setOnLongClickListener(v -> {
            startActivity(new Intent(this, SettingsActivity.class));
            return true;
        });
        webView.loadUrl(getServerUrl());

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override public void handleOnBackPressed() {
                if (webView.canGoBack()) { webView.goBack(); } else { finish(); }
            }
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null && !getServerUrl().equals(webView.getUrl())) {
            webView.loadUrl(getServerUrl());
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setGeolocationEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        if (WebViewFeature.isFeatureSupported(WebViewFeature.FORCE_DARK)) {
            WebSettingsCompat.setForceDark(settings, WebSettingsCompat.FORCE_DARK_OFF);
        }

        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return handleUrl(request.getUrl());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return handleUrl(Uri.parse(url));
            }
            @Override public void onPageFinished(WebView view, String url) {
                splashView.animate().alpha(0f).setDuration(250).withEndAction(() -> splashView.setVisibility(View.GONE)).start();
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                progressBar.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
            }
            @Override public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback callback) {
                if (ContextCompat.checkSelfPermission(WebViewActivity.this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
                    callback.invoke(origin, true, false);
                } else {
                    pendingGeoOrigin = origin;
                    pendingGeoCallback = callback;
                    ActivityCompat.requestPermissions(WebViewActivity.this, new String[]{Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION}, LOCATION_REQUEST_CODE);
                }
            }
        });
    }

    private boolean handleUrl(Uri uri) {
        String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase();
        if ("http".equals(scheme) || "https".equals(scheme)) {
            Uri server = Uri.parse(getServerUrl());
            if (sameOrigin(server, uri)) return false;
        }
        try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (ActivityNotFoundException ignored) { }
        return true;
    }

    private boolean sameOrigin(Uri a, Uri b) {
        int ap = a.getPort() == -1 ? ("https".equals(a.getScheme()) ? 443 : 80) : a.getPort();
        int bp = b.getPort() == -1 ? ("https".equals(b.getScheme()) ? 443 : 80) : b.getPort();
        return safeEquals(a.getScheme(), b.getScheme()) && safeEquals(a.getHost(), b.getHost()) && ap == bp;
    }

    private static boolean safeEquals(String a, String b) { return a == null ? b == null : a.equalsIgnoreCase(b); }

    protected String getServerUrl() {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        String value = prefs.getString(PREF_SERVER_URL, DEFAULT_SERVER_URL);
        if (value == null || value.trim().isEmpty()) return DEFAULT_SERVER_URL;
        return normalizeUrl(value.trim());
    }

    public static String normalizeUrl(String url) {
        if (!url.startsWith("http://") && !url.startsWith("https://")) url = "http://" + url;
        return url.endsWith("/") ? url : url + "/";
    }

    private FrameLayout createSplashView() {
        FrameLayout splash = new FrameLayout(this);
        splash.setBackgroundColor(ContextCompat.getColor(this, R.color.icekey_dark));
        ImageView logo = new ImageView(this);
        logo.setImageResource(R.drawable.ic_launcher);
        logo.setContentDescription(getString(R.string.app_name));
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(dp(128), dp(128), Gravity.CENTER);
        splash.addView(logo, lp);
        return splash;
    }

    @Override public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == LOCATION_REQUEST_CODE && pendingGeoCallback != null) {
            boolean granted = grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;
            pendingGeoCallback.invoke(pendingGeoOrigin, granted, false);
            pendingGeoOrigin = null;
            pendingGeoCallback = null;
        }
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
