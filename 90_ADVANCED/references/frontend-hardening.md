# Frontend Hardening Reference

## UI states to implement

- Loading
- Empty
- Partial data
- Permission denied
- Validation error
- Network error
- Retryable failure
- Irrecoverable failure
- Offline/degraded mode where relevant

## Accessibility checks

- Semantic HTML first
- Keyboard-only path for all critical flows
- Visible focus
- Programmatic labels and descriptions
- Error messages connected to fields
- Color contrast and non-color cues
- Reduced motion handling where appropriate

## Performance checks

- Route-level bundle budget
- Lazy loading for heavy routes/components
- Image optimization and responsive sizing
- Avoid unnecessary client hydration
- Avoid repeated render loops
- Measure before memoizing

## Client security checks

- Do not expose secrets in browser bundles
- Treat route guards as UX, not authorization
- Validate and encode untrusted content
- Apply CSP and secure headers from server/CDN
- Do not log sensitive data to analytics or client telemetry
