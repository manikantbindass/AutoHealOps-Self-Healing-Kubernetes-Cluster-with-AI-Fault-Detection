import { useEffect, useRef, useState, useCallback } from 'react';

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const ws = useRef(null);
  const reconnectTimeout = useRef(null);

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(WS_URL);
      ws.current.onopen = () => { setIsConnected(true); console.log('WS connected'); };
      ws.current.onmessage = (e) => setLastMessage(JSON.parse(e.data));
      ws.current.onclose = () => {
        setIsConnected(false);
        reconnectTimeout.current = setTimeout(connect, 3000);
      };
      ws.current.onerror = () => ws.current.close();
    } catch (e) {
      reconnectTimeout.current = setTimeout(connect, 3000);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeout.current);
      ws.current?.close();
    };
  }, [connect]);

  return { isConnected, lastMessage };
}
