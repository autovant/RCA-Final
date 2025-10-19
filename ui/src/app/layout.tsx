import './globals.css';

export const metadata = {
  title: "RCA Engine - Automation Support Control Plane",
  description: "Automated root-cause analysis and ticket orchestration for support teams.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-dark-bg-primary text-dark-text-primary min-h-screen antialiased">
        <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(16,110,190,0.28),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(0,183,195,0.18),_transparent_50%)]" />
          <div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg width=\'320\' height=\'320\' viewBox=\'0 0 320 320\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' stroke=\'rgba(255,255,255,0.04)\' stroke-width=\'1\'%3E%3Cpath d=\'M0 40h320M0 80h320M0 120h320M0 160h320M0 200h320M0 240h320M0 280h320M40 0v320M80 0v320M120 0v320M160 0v320M200 0v320M240 0v320M280 0v320\'/%3E%3C/g%3E%3C/svg%3E')] opacity-60" />
          <div className="absolute -left-32 top-32 h-72 w-72 rounded-full bg-fluent-blue-500/10 blur-[120px]" />
          <div className="absolute -right-24 bottom-24 h-64 w-64 rounded-full bg-fluent-info/20 blur-[120px]" />
        </div>
        
        {/* Main container */}
        <div className="min-h-screen">
          {children}
        </div>
      </body>
    </html>
  );
}
