package com.lumiere.scantron;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.DownloadManager;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.view.View;
import android.webkit.DownloadListener;
import android.webkit.PermissionRequest;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private WebView webView;
    private TextView tvServerStatus;
    private Button btnConfigServer;
    private SharedPreferences prefs;

    private static final String PREF_NAME = "ScantronPrefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final int REQUEST_CODE_FILE_CHOOSER = 1001;
    private static final int REQUEST_CODE_PERMISSIONS = 1002;

    private ValueCallback<Uri[]> mFilePathCallback;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences(PREF_NAME, MODE_PRIVATE);

        webView = findViewById(R.id.webView);
        tvServerStatus = findViewById(R.id.tvServerStatus);
        btnConfigServer = findViewById(R.id.btnConfigServer);

        setupWebView();
        requestAppPermissions();

        btnConfigServer.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showConfigDialog();
            }
        });

        loadCurrentUrl();
    }

    private void requestAppPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{
                        Manifest.permission.CAMERA,
                        Manifest.permission.READ_EXTERNAL_STORAGE,
                        Manifest.permission.WRITE_EXTERNAL_STORAGE
                }, REQUEST_CODE_PERMISSIONS);
            }
        }
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setSupportZoom(true);
        settings.setBuiltInZoomControls(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("file://")) {
                    view.loadUrl(url);
                    return true;
                }
                return false;
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            // Grant camera access to webview
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        request.grant(request.getResources());
                    }
                });
            }

            // Handle file and camera capture
            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback,
                                            FileChooserParams fileChooserParams) {
                if (mFilePathCallback != null) {
                    mFilePathCallback.onReceiveValue(null);
                }
                mFilePathCallback = filePathCallback;

                Intent intent = fileChooserParams.createIntent();
                try {
                    startActivityForResult(intent, REQUEST_CODE_FILE_CHOOSER);
                } catch (Exception e) {
                    mFilePathCallback = null;
                    Toast.makeText(MainActivity.this, "Error abriendo selector de cámara/archivos", Toast.LENGTH_SHORT).show();
                    return false;
                }
                return true;
            }
        });

        // Handle PDF downloads
        webView.setDownloadListener(new DownloadListener() {
            @Override
            public void onDownloadStart(String url, String userAgent, String contentDisposition, String mimetype, long contentLength) {
                try {
                    DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                    request.setMimeType(mimetype);
                    request.setDescription("Descargando plantilla de examen PDF...");
                    String filename = URLUtil.guessFileName(url, contentDisposition, mimetype);
                    request.setTitle(filename);
                    request.allowScanningByMediaScanner();
                    request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                    request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename);

                    DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                    dm.enqueue(request);
                    Toast.makeText(MainActivity.this, "Descargando: " + filename, Toast.LENGTH_LONG).show();
                } catch (Exception e) {
                    // Fallback to external browser
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                }
            }
        });
    }

    private void loadCurrentUrl() {
        String savedUrl = prefs.getString(KEY_SERVER_URL, "");
        if (savedUrl != null && !savedUrl.trim().isEmpty()) {
            tvServerStatus.setText("Servidor: " + savedUrl);
            webView.loadUrl(savedUrl);
        } else {
            tvServerStatus.setText("Modo Local (Configura URL de Railway)");
            webView.loadUrl("file:///android_asset/www/index.html");
        }
    }

    private void showConfigDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("URL del Servidor Scantron");
        builder.setMessage("Ingresa la URL de tu backend desplegado en Railway (ejemplo: https://mi-scantron.up.railway.app) o tu IP local.");

        final EditText input = new EditText(this);
        String currentUrl = prefs.getString(KEY_SERVER_URL, "");
        input.setText(currentUrl);
        input.setHint("https://tu-proyecto.up.railway.app");
        builder.setView(input);

        builder.setPositiveButton("Guardar y Conectar", new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int which) {
                String newUrl = input.getText().toString().trim();
                if (!newUrl.isEmpty() && !newUrl.startsWith("http://") && !newUrl.startsWith("https://")) {
                    newUrl = "https://" + newUrl;
                }
                prefs.edit().putString(KEY_SERVER_URL, newUrl).apply();
                loadCurrentUrl();
                Toast.makeText(MainActivity.this, "Servidor actualizado", Toast.LENGTH_SHORT).show();
            }
        });

        builder.setNeutralButton("Usar Modo Local", new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int which) {
                prefs.edit().putString(KEY_SERVER_URL, "").apply();
                loadCurrentUrl();
            }
        });

        builder.setNegativeButton("Cancelar", null);
        builder.show();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_CODE_FILE_CHOOSER) {
            if (mFilePathCallback != null) {
                Uri[] results = null;
                if (resultCode == Activity.RESULT_OK && data != null) {
                    String dataString = data.getDataString();
                    if (dataString != null) {
                        results = new Uri[]{Uri.parse(dataString)};
                    } else if (data.getClipData() != null) {
                        final int count = data.getClipData().getItemCount();
                        results = new Uri[count];
                        for (int i = 0; i < count; i++) {
                            results[i] = data.getClipData().getItemAt(i).getUri();
                        }
                    }
                }
                mFilePathCallback.onReceiveValue(results);
                mFilePathCallback = null;
            }
        }
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
