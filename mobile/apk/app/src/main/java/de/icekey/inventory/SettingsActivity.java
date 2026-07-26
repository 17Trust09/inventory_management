package de.icekey.inventory;

import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.MenuItem;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

public class SettingsActivity extends AppCompatActivity {
    private EditText serverUrlInput;

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getSupportActionBar();

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(20);
        layout.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("Icekey Inventory Server URL");
        title.setTextSize(20);
        title.setPadding(0, 0, 0, dp(12));
        layout.addView(title);

        serverUrlInput = new EditText(this);
        serverUrlInput.setSingleLine(true);
        serverUrlInput.setInputType(android.text.InputType.TYPE_TEXT_VARIATION_URI);
        serverUrlInput.setImeOptions(EditorInfo.IME_ACTION_DONE);
        serverUrlInput.setText(getSharedPreferences(WebViewActivity.PREFS_NAME, MODE_PRIVATE).getString(WebViewActivity.PREF_SERVER_URL, WebViewActivity.DEFAULT_SERVER_URL));
        layout.addView(serverUrlInput, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        Button save = new Button(this);
        save.setText("Speichern");
        save.setOnClickListener(v -> saveUrl());
        layout.addView(save);

        Button reset = new Button(this);
        reset.setText("Standard wiederherstellen");
        reset.setOnClickListener(v -> {
            serverUrlInput.setText(WebViewActivity.DEFAULT_SERVER_URL);
            saveUrl();
        });
        layout.addView(reset);

        setContentView(layout);
    }

    private void saveUrl() {
        String normalized = WebViewActivity.normalizeUrl(serverUrlInput.getText().toString().trim());
        SharedPreferences prefs = getSharedPreferences(WebViewActivity.PREFS_NAME, MODE_PRIVATE);
        prefs.edit().putString(WebViewActivity.PREF_SERVER_URL, normalized).apply();
        Toast.makeText(this, "Server URL gespeichert", Toast.LENGTH_SHORT).show();
    }

    @Override public boolean onOptionsItemSelected(MenuItem item) {
        if (item.getItemId() == android.R.id.home) { finish(); return true; }
        return super.onOptionsItemSelected(item);
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
