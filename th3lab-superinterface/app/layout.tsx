import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TH3LAB MCP Console",
  description: "Interfaz de chat para TH3LAB MCP"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
