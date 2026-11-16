import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const publicPaths = ['/login', '/register'];
const authPaths = ['/dashboard', '/projects'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const authCookie = request.cookies.get('auth-storage');
  
  const isPublicPath = publicPaths.some(path => pathname.startsWith(path));
  const isAuthPath = authPaths.some(path => pathname.startsWith(path));
  
  // If accessing auth path without auth, redirect to login
  if (isAuthPath && !authCookie) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  
  // If accessing public path with auth, redirect to dashboard
  if (isPublicPath && authCookie) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\.png$).*)',
  ],
};