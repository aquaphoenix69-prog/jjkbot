import './globals.css';

export const metadata = {
  title: "SenaBot — Sena's Digi-Love Companion 💕",
  description: 'A love letter in code, from Digi to Sena.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:ital,wght@0,700;1,700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-gradient-love min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
