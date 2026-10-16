# Admin Phase 3: Layout and Route Protection

The existing customer prediction page remains at `/`. The administrator application is isolated beneath `/admin`.

## Routes implemented

- `/admin/login`: public administrator login
- `/admin`: protected layout and phase-status overview
- All requested admin child routes: protected placeholders ready for their scheduled feature phases

The sidebar removes entries for permissions the current administrator lacks. This is usability only; FastAPI permission dependencies remain the authoritative authorization boundary.

## Session behavior

The access token exists only in React memory. The opaque refresh token is stored in session storage so a tab refresh can rotate it and reconstruct the session. Session storage remains accessible to injected JavaScript, so production should prefer a backend-for-frontend with a Secure, HttpOnly, SameSite refresh cookie and a strict content-security policy.

## Responsive and accessibility behavior

- Collapsible desktop sidebar
- Mobile navigation drawer and dismissible backdrop
- Keyboard-usable native controls and labeled icon buttons
- Active-route indication
- Dark and light themes saved as a device preference
- Loading and authentication-error states
- Permission-filtered navigation

The overview intentionally contains no fabricated monitoring values. Measured summary APIs, cards, charts, and activity data belong to Phase 4.
