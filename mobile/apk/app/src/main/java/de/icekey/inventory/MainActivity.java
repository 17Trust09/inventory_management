package de.icekey.inventory;

import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.inputmethod.EditorInfo;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.Nullable;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;

import com.google.android.material.button.MaterialButton;
import com.google.android.material.card.MaterialCardView;
import com.google.android.material.textfield.TextInputEditText;
import com.google.android.material.textfield.TextInputLayout;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/** Launcher screen for selecting and saving Icekey Inventory servers. */
public class MainActivity extends AppCompatActivity {
    static final String PREFS_NAME = WebViewActivity.PREFS_NAME;
    static final String PREF_SERVER_URL = WebViewActivity.PREF_SERVER_URL;
    static final String PREF_SAVED_SERVERS = "saved_servers";

    private static final String DEFAULT_LOCAL_NAME = "Unraid (Lokal)";
    private static final String DEFAULT_LOCAL_URL = "http://192.168.178.69:18000";
    private static final String DEFAULT_TAILSCALE_NAME = "Raspberry Pi (Tailscale)";
    private static final String DEFAULT_TAILSCALE_URL = "http://100.84.57.80:8000";

    private TextInputEditText serverInput;
    private LinearLayout serverList;
    private SharedPreferences prefs;

    @Override protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        seedDefaultServersIfNeeded();
        getWindow().setStatusBarColor(ContextCompat.getColor(this, R.color.icekey_darkest));
        getWindow().setNavigationBarColor(ContextCompat.getColor(this, R.color.icekey_darkest));
        setContentView(createContentView());
        serverInput.setText(stripScheme(prefs.getString(PREF_SERVER_URL, DEFAULT_LOCAL_URL)));
        renderServerList();
    }

    private ScrollView createContentView() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(ContextCompat.getColor(this, R.color.icekey_darkest));
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(24), dp(32), dp(24), dp(24));
        scroll.addView(root, new ScrollView.LayoutParams(ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));

        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER);
        header.setOrientation(LinearLayout.VERTICAL);
        root.addView(header, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        ImageView icon = new ImageView(this);
        icon.setImageResource(R.drawable.ic_launcher);
        icon.setContentDescription(getString(R.string.app_name));
        header.addView(icon, new LinearLayout.LayoutParams(dp(88), dp(88)));
        TextView title = text(R.string.app_title, 28, Color.WHITE, true);
        title.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams titleParams = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        titleParams.setMargins(0, dp(14), 0, dp(6));
        header.addView(title, titleParams);
        TextView subtitle = text(R.string.server_selection_subtitle, 15, 0xB3FFFFFF, false);
        subtitle.setGravity(Gravity.CENTER);
        header.addView(subtitle);

        MaterialCardView inputCard = card(false);
        LinearLayout.LayoutParams inputCardParams = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        inputCardParams.setMargins(0, dp(28), 0, dp(18));
        root.addView(inputCard, inputCardParams);
        LinearLayout inputSection = new LinearLayout(this);
        inputSection.setOrientation(LinearLayout.VERTICAL);
        inputSection.setPadding(dp(18), dp(18), dp(18), dp(18));
        inputCard.addView(inputSection);

        TextInputLayout inputLayout = new TextInputLayout(this);
        inputLayout.setHint(getString(R.string.server_address_label));
        inputLayout.setBoxBackgroundMode(TextInputLayout.BOX_BACKGROUND_OUTLINE);
        inputLayout.setBoxStrokeColor(ContextCompat.getColor(this, R.color.icekey_accent));
        inputLayout.setHintTextColor(android.content.res.ColorStateList.valueOf(0xB3FFFFFF));
        inputLayout.setBoxBackgroundColor(0x1410101F);
        inputSection.addView(inputLayout, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        serverInput = new TextInputEditText(inputLayout.getContext());
        serverInput.setSingleLine(true);
        serverInput.setInputType(InputType.TYPE_TEXT_VARIATION_URI);
        serverInput.setImeOptions(EditorInfo.IME_ACTION_GO);
        serverInput.setHint(R.string.server_address_placeholder);
        serverInput.setTextColor(Color.WHITE);
        serverInput.setHintTextColor(0x80FFFFFF);
        serverInput.setOnEditorActionListener((v, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_GO || actionId == EditorInfo.IME_ACTION_DONE) { connectFromInput(); return true; }
            return false;
        });
        inputLayout.addView(serverInput);

        LinearLayout buttonRow = new LinearLayout(this);
        buttonRow.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams buttonRowParams = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        buttonRowParams.setMargins(0, dp(14), 0, 0);
        inputSection.addView(buttonRow, buttonRowParams);
        MaterialButton newServer = new MaterialButton(this, null, com.google.android.material.R.attr.materialButtonOutlinedStyle);
        newServer.setText(R.string.new_server_button);
        newServer.setTextColor(Color.WHITE);
        newServer.setStrokeColor(android.content.res.ColorStateList.valueOf(0x59FFFFFF));
        newServer.setOnClickListener(v -> { serverInput.setText(""); serverInput.requestFocus(); });
        LinearLayout.LayoutParams newParams = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        newParams.setMargins(0, 0, dp(10), 0);
        buttonRow.addView(newServer, newParams);
        MaterialButton connect = new MaterialButton(this);
        connect.setText(R.string.connect_button);
        connect.setBackgroundColor(ContextCompat.getColor(this, R.color.icekey_accent));
        connect.setTextColor(Color.WHITE);
        connect.setOnClickListener(v -> connectFromInput());
        buttonRow.addView(connect, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        root.addView(text(R.string.saved_servers_title, 18, Color.WHITE, true));
        serverList = new LinearLayout(this);
        serverList.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams listParams = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        listParams.setMargins(0, dp(10), 0, 0);
        root.addView(serverList, listParams);
        return scroll;
    }

    private TextView text(int resId, int sp, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(resId);
        view.setTextSize(sp);
        view.setTextColor(color);
        if (bold) view.setTypeface(view.getTypeface(), android.graphics.Typeface.BOLD);
        return view;
    }

    private MaterialCardView card(boolean active) {
        MaterialCardView card = new MaterialCardView(this);
        card.setCardBackgroundColor(ContextCompat.getColor(this, R.color.icekey_dark));
        card.setStrokeColor(active ? ContextCompat.getColor(this, R.color.icekey_accent) : 0x26FFFFFF);
        card.setStrokeWidth(dp(active ? 2 : 1));
        card.setRadius(dp(20));
        return card;
    }

    private void renderServerList() {
        serverList.removeAllViews();
        JSONArray servers = getSavedServers();
        String currentUrl = WebViewActivity.normalizeUrl(prefs.getString(PREF_SERVER_URL, DEFAULT_LOCAL_URL));
        for (int i = 0; i < servers.length(); i++) {
            JSONObject server = servers.optJSONObject(i);
            if (server == null) continue;
            String name = server.optString("name", getString(R.string.saved_server_fallback_name));
            String url = WebViewActivity.normalizeUrl(server.optString("url", ""));
            boolean lastUsed = url.equals(currentUrl) || server.optBoolean("lastUsed", false);
            serverList.addView(createServerRow(i, name, url, lastUsed));
        }
    }

    private MaterialCardView createServerRow(int index, String name, String url, boolean lastUsed) {
        MaterialCardView rowCard = card(lastUsed);
        rowCard.setClickable(true);
        rowCard.setFocusable(true);
        rowCard.setOnClickListener(v -> openServer(url));
        rowCard.setOnLongClickListener(v -> { confirmDeleteServer(index, name); return true; });
        LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        cardParams.setMargins(0, 0, 0, dp(10));
        rowCard.setLayoutParams(cardParams);
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(16), dp(14), dp(8), dp(14));
        rowCard.addView(row);
        LinearLayout labels = new LinearLayout(this);
        labels.setOrientation(LinearLayout.VERTICAL);
        row.addView(labels, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        TextView title = new TextView(this);
        title.setText(lastUsed ? name + "  •  " + getString(R.string.last_used_label) : name);
        title.setTextColor(Color.WHITE);
        title.setTextSize(16);
        title.setTypeface(title.getTypeface(), android.graphics.Typeface.BOLD);
        labels.addView(title);
        TextView subtitle = new TextView(this);
        subtitle.setText(url);
        subtitle.setTextColor(0xB3FFFFFF);
        subtitle.setTextSize(13);
        subtitle.setPadding(0, dp(4), 0, 0);
        labels.addView(subtitle);
        ImageButton delete = new ImageButton(this);
        delete.setImageResource(android.R.drawable.ic_menu_delete);
        delete.setContentDescription(getString(R.string.delete_server_content_description, name));
        delete.setColorFilter(0xB3FFFFFF);
        delete.setBackgroundColor(Color.TRANSPARENT);
        delete.setOnClickListener(v -> confirmDeleteServer(index, name));
        row.addView(delete, new LinearLayout.LayoutParams(dp(48), dp(48)));
        return rowCard;
    }

    private void connectFromInput() {
        String value = serverInput.getText() == null ? "" : serverInput.getText().toString().trim();
        if (value.isEmpty()) { Toast.makeText(this, R.string.server_address_required, Toast.LENGTH_SHORT).show(); return; }
        openServer(WebViewActivity.normalizeUrl(value));
    }

    private void openServer(String url) {
        String normalized = WebViewActivity.normalizeUrl(url);
        saveServer(deriveServerName(normalized), normalized);
        Intent intent = new Intent(this, WebViewActivity.class);
        intent.putExtra(WebViewActivity.EXTRA_SERVER_URL, normalized);
        startActivity(intent);
    }

    private void saveServer(String name, String url) {
        JSONArray original = getSavedServers();
        JSONArray updated = new JSONArray();
        boolean found = false;
        for (int i = 0; i < original.length(); i++) {
            JSONObject item = original.optJSONObject(i);
            if (item == null) continue;
            String itemUrl = WebViewActivity.normalizeUrl(item.optString("url", ""));
            try {
                JSONObject copy = new JSONObject();
                copy.put("name", itemUrl.equals(url) ? item.optString("name", name) : item.optString("name", deriveServerName(itemUrl)));
                copy.put("url", itemUrl);
                copy.put("lastUsed", itemUrl.equals(url));
                updated.put(copy);
                if (itemUrl.equals(url)) found = true;
            } catch (JSONException ignored) { }
        }
        if (!found) {
            try {
                JSONObject item = new JSONObject();
                item.put("name", name);
                item.put("url", url);
                item.put("lastUsed", true);
                updated.put(item);
            } catch (JSONException ignored) { }
        }
        prefs.edit().putString(PREF_SERVER_URL, url).putString(PREF_SAVED_SERVERS, updated.toString()).apply();
        renderServerList();
    }

    private void confirmDeleteServer(int index, String name) {
        new AlertDialog.Builder(this)
                .setTitle(R.string.delete_server_title)
                .setMessage(getString(R.string.delete_server_message, name))
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.delete_button, (dialog, which) -> deleteServer(index))
                .show();
    }

    private void deleteServer(int index) {
        JSONArray original = getSavedServers();
        JSONArray updated = new JSONArray();
        for (int i = 0; i < original.length(); i++) {
            if (i == index) continue;
            JSONObject item = original.optJSONObject(i);
            if (item != null) updated.put(item);
        }
        prefs.edit().putString(PREF_SAVED_SERVERS, updated.toString()).apply();
        renderServerList();
    }

    private JSONArray getSavedServers() {
        String raw = prefs.getString(PREF_SAVED_SERVERS, null);
        if (raw == null || raw.trim().isEmpty()) return defaultServers();
        try { return new JSONArray(raw); } catch (JSONException e) { return defaultServers(); }
    }

    private void seedDefaultServersIfNeeded() {
        if (!prefs.contains(PREF_SAVED_SERVERS)) {
            prefs.edit().putString(PREF_SAVED_SERVERS, defaultServers().toString()).putString(PREF_SERVER_URL, DEFAULT_LOCAL_URL).apply();
        }
    }

    private JSONArray defaultServers() {
        JSONArray servers = new JSONArray();
        try {
            JSONObject local = new JSONObject();
            local.put("name", DEFAULT_LOCAL_NAME); local.put("url", DEFAULT_LOCAL_URL); local.put("lastUsed", true); servers.put(local);
            JSONObject tailscale = new JSONObject();
            tailscale.put("name", DEFAULT_TAILSCALE_NAME); tailscale.put("url", DEFAULT_TAILSCALE_URL); tailscale.put("lastUsed", false); servers.put(tailscale);
        } catch (JSONException ignored) { }
        return servers;
    }

    private String deriveServerName(String url) {
        try {
            Uri uri = Uri.parse(url);
            String host = uri.getHost();
            if (host == null || host.isEmpty()) return getString(R.string.custom_server_name);
            int port = uri.getPort();
            return port > 0 ? host + ":" + port : host;
        } catch (Exception e) { return getString(R.string.custom_server_name); }
    }

    private String stripScheme(String url) {
        if (url == null) return "";
        return url.replaceFirst("^https?://", "");
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
