import { createFileRoute, Outlet } from "@tanstack/react-router"

export const Route = createFileRoute("/_authenticated/kb/$kbId")({
  component: () => <Outlet />,
})
