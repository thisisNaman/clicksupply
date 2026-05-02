import type { ReactNode } from "react";
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "ClickSupply — AEO/GEO Platform",
    description:
        "Enterprise Answer Engine Optimization platform for the Indian market",
};

export default function RootLayout({
    children,
}: {
    children: ReactNode;
}) {
    return (
        <html lang="en" suppressHydrationWarning>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1" />
            </head>
            <body>{children}</body>
        </html>
    );
}
