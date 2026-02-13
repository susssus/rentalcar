import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ALC Car Rental Watcher",
  description: "Track Rentalcars.com prices for Alicante airport, automatic small cars",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
