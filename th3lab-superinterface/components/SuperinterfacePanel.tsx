"use client";

import { SuperinterfaceProvider } from "@superinterface/react";

interface SuperinterfacePanelProps {
  children: React.ReactNode;
}

export default function SuperinterfacePanel({ children }: SuperinterfacePanelProps) {
  const publicApiKey = process.env.NEXT_PUBLIC_SUPERINTERFACE_API_KEY;
  const assistantId = process.env.NEXT_PUBLIC_SUPERINTERFACE_ASSISTANT_ID;

  // Self-hosted wrapper ready: if keys are missing we render local chat fallback.
  if (!publicApiKey || !assistantId) {
    return <>{children}</>;
  }

  return (
    <SuperinterfaceProvider
      variables={{
        publicApiKey,
        assistantId
      }}
    >
      {children}
    </SuperinterfaceProvider>
  );
}
