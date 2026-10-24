import { useEffect, useState } from "react";
import { websocketUrl } from "../services/api";

export function useWebSocket(onUpdate, enabled = true) {
  const [status, setStatus] = useState("connecting");
  useEffect(() => {
    if (!enabled) return;
    let stopped = false,
      socket,
      timer,
      tries = 0;
    const connect = () => {
      if (stopped) return;
      setStatus(tries ? "reconnecting" : "connecting");
      try {
        socket = new WebSocket(websocketUrl());
      } catch {
        setStatus("disconnected");
        timer = setTimeout(connect, Math.min(30000, 1000 * 2 ** tries++));
        return;
      }
      socket.onopen = () => {
        tries = 0;
        setStatus("connected");
        const token = sessionStorage.getItem("token");
        if (token) socket.send(JSON.stringify({ token }));
      };
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "operational_update" && message.overview)
            onUpdate(message.overview);
        } catch {
          setStatus("invalid message");
        }
      };
      socket.onerror = () => socket.close();
      socket.onclose = () => {
        if (stopped) return;
        setStatus("reconnecting");
        timer = setTimeout(connect, Math.min(30000, 1000 * 2 ** tries++));
      };
    };
    connect();
    return () => {
      stopped = true;
      clearTimeout(timer);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [onUpdate, enabled]);
  return { status };
}
