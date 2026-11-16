import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: 'Micro Drama SaaS',
  description: 'AI-powered Micro Drama Production SaaS Platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} antialiased`}>
      <body className="min-h-screen bg-dark-50 dark:bg-dark-950 text-dark-900 dark:text-dark-50">
        {children}
      </body>
    </html>
  );
}