**Connectivity Fixes:**

1.  **Refactored `AppState`:** Now serves as the single source of truth for the `ApiClient` and server URL.
2.  **Updated Providers:** `ConversationProvider`, `NotesProvider`, and `SettingsProvider` now receive the `ApiClient` from `AppState` instead of using a hardcoded `localhost` instance.
3.  **Wired `main.dart`:** Used `ChangeNotifierProxyProvider` to inject the updated `ApiClient` into dependent providers.
4.  **Updated `ServerSetupScreen`:** Now correctly updates `AppState` (in addition to saving to SharedPreferences) so the change takes effect immediately without a restart.

**Status:**
The app is built and configured to allow connecting to remote servers (like `10.0.0.149:5001`). Launching the app via `flutter run -d chrome` will allow testing this functionality.