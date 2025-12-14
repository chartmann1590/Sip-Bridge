The Android emulator setup is now complete and the app has been successfully deployed.

**Status:**
-   **Emulator:** `Pixel_5_API_30` is running and online.
-   **App:** Installed (`com.example.sip_bridge_flutter`) and launched.
-   **Fixes Applied:**
    -   Resolved a crash in `SplashScreen` caused by incompatible navigation calls. Switched from `Navigator.pushReplacementNamed` to `context.go` (GoRouter).
    -   Refactored `AppState` and Providers to support dynamic server URLs.
    -   Fixed asset and icon issues.

**Instructions:**
1.  Unlock the emulator if it is locked.
2.  The app should be running. If not, find "sip_bridge_flutter" in the app drawer and launch it.
3.  On the "Server Setup" screen, enter your remote server details:
    -   **Server:** `http://10.0.0.149:5001`
    -   **WebSocket:** `ws://10.0.0.149:5001`
4.  Tap "Connect".

**Note:** The emulator logs show DNS errors for `google_fonts` (`fonts.gstatic.com`). This means the emulator might not have internet access or DNS is misconfigured. This will only affect font downloading; the app functionality should work if the emulator can reach `10.0.0.149` (local network). If it cannot reach the local network, you may need to configure the emulator's network settings (e.g., set proxy or check DNS).
