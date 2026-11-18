import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Auth is client-side in this app: the JWT lives in localStorage
// (zustand persist 'auth-storage') and the API axios interceptor attaches
// it; DashboardLayout + the 401 interceptor redirect to /login when it is
// missing/invalid. The previous middleware read a cookie named
// 'auth-storage' that is never set anywhere, so /dashboard and /projects
// always redirected back to /login right after a successful login
// (audit F-04). There is intentionally no server-side guard here — do not
// re-add a cookie check without also setting that cookie at login.

export function middleware(request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\.png$).*)',
  ],
};
