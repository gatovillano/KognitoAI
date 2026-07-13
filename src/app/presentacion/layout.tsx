import PresentacionClientLayout from "./PresentacionClientLayout";

export default function PresentacionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <PresentacionClientLayout>{children}</PresentacionClientLayout>;
}