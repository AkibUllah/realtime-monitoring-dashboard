import { useEffect, useRef, useState, type Dispatch } from 'react';
import { nextDelay } from '@/lib/backoff';
import type { MetricsAction } from '@/lib/metrics';
import type { ServerMessage } from '@/lib/types';

export type SocketStatus = 'connecting' | 'open' | 'reconnecting' | 'closed';

export interface SocketInfo { status: SocketStatus; attempts: number; lastMessageAt: number | null }

/**
 * Keeps a WebSocket open to the metrics stream, reconnecting with jittered exponential
 * backoff, and dispatches every message into the metrics reducer.
 */
export function useMetricsSocket(url: string, dispatch: Dispatch<MetricsAction>, enabled = true): SocketInfo {
  const [info, setInfo] = useState<SocketInfo>({ status: 'connecting', attempts: 0, lastMessageAt: null });
  const attemptsRef = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    let socket: WebSocket | null = null;
    let timer: number | undefined;
    let pingTimer: number | undefined;
    let disposed = false;

    const connect = () => {
      setInfo((s) => ({ ...s, status: attemptsRef.current === 0 ? 'connecting' : 'reconnecting', attempts: attemptsRef.current }));
      socket = new WebSocket(url);
      socket.onopen = () => {
        attemptsRef.current = 0;
        setInfo({ status: 'open', attempts: 0, lastMessageAt: null });
        pingTimer = window.setInterval(() => socket?.readyState === WebSocket.OPEN && socket.send('{"type":"ping"}'), 25_000);
      };
      socket.onmessage = (ev) => {
        try {
          const message = JSON.parse(ev.data as string) as ServerMessage;
          dispatch({ type: 'message', message });
          setInfo((s) => ({ ...s, lastMessageAt: Date.now() }));
        } catch {
          /* malformed frame: ignore */
        }
      };
      socket.onclose = () => {
        window.clearInterval(pingTimer);
        if (disposed) return;
        const delay = nextDelay(attemptsRef.current);
        attemptsRef.current += 1;
        setInfo((s) => ({ ...s, status: 'reconnecting', attempts: attemptsRef.current }));
        timer = window.setTimeout(connect, delay);
      };
      socket.onerror = () => socket?.close();
    };

    connect();
    return () => {
      disposed = true;
      window.clearTimeout(timer);
      window.clearInterval(pingTimer);
      socket?.close();
      setInfo((s) => ({ ...s, status: 'closed' }));
    };
  }, [url, dispatch, enabled]);

  return info;
}
