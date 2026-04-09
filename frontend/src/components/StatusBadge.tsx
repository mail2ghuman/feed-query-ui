import { CheckCircle, XCircle, Loader2 } from "lucide-react";

interface StatusBadgeProps {
  status: "connected" | "disconnected" | "connecting";
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const config = {
    connected: {
      icon: <CheckCircle className="w-3.5 h-3.5" />,
      text: "Backend Connected",
      className: "bg-green-50 text-green-700 border-green-200",
    },
    disconnected: {
      icon: <XCircle className="w-3.5 h-3.5" />,
      text: "Backend Disconnected",
      className: "bg-red-50 text-red-700 border-red-200",
    },
    connecting: {
      icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
      text: "Connecting...",
      className: "bg-yellow-50 text-yellow-700 border-yellow-200",
    },
  };

  const { icon, text, className } = config[status];

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${className}`}
    >
      {icon}
      {text}
    </div>
  );
}
