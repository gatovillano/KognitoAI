// En: src/app/(dashboard)/layout.tsx
import { Sidebar } from "@/components/Sidebar";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ResizablePanelGroup
      direction="horizontal"
      className="min-h-screen w-full rounded-lg border-0"
    >
      <ResizablePanel defaultSize={20} minSize={15} maxSize={25}>
        <Sidebar />
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={80}>
        {children}
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}