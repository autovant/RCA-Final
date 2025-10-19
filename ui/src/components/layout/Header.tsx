"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from '@/components/ui';

interface HeaderProps {
  title?: string;
  subtitle?: string;
  isAuthenticated?: boolean;
  showAuthActions?: boolean;
  onLogin?: () => void;
  onSignup?: () => void;
  onLogout?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  title = "Perficient RCA Console",
  subtitle = "Automation Command Surface",
  isAuthenticated = false,
  showAuthActions = false,
  onLogin,
  onSignup,
  onLogout,
}) => {
  const pathname = usePathname();

  const navItems = [
    {
      href: "/",
      label: "Dashboard",
      icon: (
        <svg className="w-4 h-4 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      )
    },
    {
      href: "/investigation",
      label: "Investigate",
      icon: (
        <svg className="w-4 h-4 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h8M8 11h8m-8 4h5m7 0a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    },
    {
      href: "/related",
      label: "Related",
      icon: (
        <svg className="w-4 h-4 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7H7a2 2 0 00-2 2v8m0 0a2 2 0 002 2h8m-8-2l3.586-3.586a2 2 0 012.828 0L17 17m-3.586-3.586L17 10" />
        </svg>
      )
    },
    {
      href: "/features",
      label: "Features",
      icon: (
        <svg className="w-4 h-4 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
        </svg>
      )
    },
    {
      href: "/about",
      label: "About",
      icon: (
        <svg className="w-4 h-4 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2h-2.5a1 1 0 01-.894-.553l-.724-1.447A1 1 0 0013.5 3h-3a1 1 0 00-.882.5l-.724 1.447A1 1 0 018 5H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      )
    },
    {
      href: "/jobs",
      label: "Jobs",
      icon: (
        <svg className="w-4 h-4 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      )
    },
    {
      href: "/tickets",
      label: "Tickets",
      icon: (
        <svg className="w-4 h-4 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      )
    },
    {
      href: "/watcher",
      label: "Watcher",
      icon: (
        <svg className="w-4 h-4 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
        </svg>
      )
    },
    {
      href: "/docs",
      label: "Docs",
      icon: (
        <svg className="w-4 h-4 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      )
    }
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-dark-border/40 bg-dark-bg-primary/70 backdrop-blur-2xl relative">
      <div className="absolute inset-0 pointer-events-none bg-gradient-to-r from-transparent via-fluent-blue-500/10 to-transparent" aria-hidden="true" />
      <div className="relative">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-4 py-4 lg:h-16 lg:flex-nowrap lg:py-0">
            {/* Logo and Title */}
            <div className="flex min-w-0 items-center gap-4">
              <div className="relative flex items-center justify-center">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-fluent-blue-500 via-fluent-info/80 to-fluent-blue-400 shadow-[0_10px_30px_rgba(14,116,220,0.25)]">
                  <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                  </svg>
                </div>
                <div className="absolute -inset-2 rounded-2xl bg-fluent-blue-500/40 blur-2xl" aria-hidden="true" />
              </div>

              <div className="flex min-w-0 flex-col leading-tight">
                <h1 className="truncate text-lg font-semibold tracking-tight text-dark-text-primary">
                  {title}
                </h1>
                <p className="visible text-[0.65rem] font-medium uppercase tracking-[0.28em] text-dark-text-tertiary sm:text-xs">
                  {subtitle}
                </p>
              </div>
            </div>

            {/* Navigation */}
            <nav className="hidden lg:flex items-center gap-2">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                const className = isActive ? "nav-item nav-item-active" : "nav-item";

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={className}
                    aria-current={isActive ? "page" : undefined}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            <div className="flex flex-1 flex-wrap items-center justify-end gap-3">
              <nav className="order-3 flex basis-full items-center justify-between gap-2 overflow-x-auto rounded-2xl border border-dark-border/40 bg-dark-bg-tertiary/60 px-2 py-2 text-sm lg:hidden sm:order-none sm:basis-auto sm:rounded-full sm:border-transparent sm:bg-transparent sm:px-0 sm:py-0">
                {navItems.map((item) => {
                  const isActive = pathname === item.href;
                  const className = isActive ? "nav-item nav-item-active" : "nav-item";

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`${className} px-3 py-1.5`}
                      aria-current={isActive ? "page" : undefined}
                    >
                      {item.icon}
                      <span className="sr-only">{item.label}</span>
                    </Link>
                  );
                })}
              </nav>

              {/* Security Badge - PII Protection Enabled */}
              <div className="hidden lg:flex items-center gap-2 rounded-full border border-green-500/30 bg-green-500/10 px-3 py-1.5 text-xs font-bold tracking-wide text-green-400 shadow-lg shadow-green-500/10">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span>PII PROTECTED</span>
              </div>

              {/* Status Indicator */}
              <div className="hidden sm:flex items-center gap-2 rounded-full border border-dark-border/50 bg-dark-bg-tertiary/60 px-4 py-1.5 text-xs font-semibold tracking-[0.2em] text-dark-text-secondary">
                <span className="relative inline-flex h-2 w-2 items-center justify-center">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-fluent-success/60 blur-sm" aria-hidden="true" />
                  <span className="relative inline-block h-2 w-2 rounded-full bg-fluent-success" />
                </span>
                STABLE
              </div>

              {showAuthActions && (
                <div className="flex items-center gap-2">
                  {isAuthenticated ? (
                    onLogout && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={onLogout}
                        className="hidden sm:inline-flex"
                      >
                        Sign out
                      </Button>
                    )
                  ) : (
                    <>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => onLogin?.()}
                        className="hidden sm:inline-flex"
                      >
                        Log in
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => onSignup?.()}
                        className="hidden sm:inline-flex"
                      >
                        Create account
                      </Button>
                    </>
                  )}

                  <div className="flex items-center gap-2 sm:hidden">
                    {isAuthenticated ? (
                      onLogout && (
                        <button
                          type="button"
                          onClick={onLogout}
                          className="rounded-xl border border-dark-border/50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-dark-text-secondary hover:bg-dark-bg-tertiary/60"
                        >
                          Sign out
                        </button>
                      )
                    ) : (
                      <>
                        <button
                          type="button"
                          onClick={() => onLogin?.()}
                          className="rounded-xl border border-dark-border/50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-dark-text-secondary hover:bg-dark-bg-tertiary/60"
                        >
                          Log in
                        </button>
                        <button
                          type="button"
                          onClick={() => onSignup?.()}
                          className="rounded-xl border border-dark-border/50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-dark-text-secondary hover:bg-dark-bg-tertiary/60"
                        >
                          Join
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Settings */}
              <button className="icon-button" aria-label="Open settings">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
