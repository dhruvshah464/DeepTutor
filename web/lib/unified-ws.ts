/**
 * Unified WebSocket Client
 *
 * Connects to the single `/api/v1/ws` endpoint and provides
 * a typed streaming interface for the new ChatOrchestrator protocol.
 */

import { wsUrl } from "./api";

// ---- StreamEvent types (mirror Python StreamEventType) ----

export type StreamEventType =
  | "stage_start"
  | "stage_end"
  | "thinking"
  | "observation"
  | "content"
  | "tool_call"
  | "tool_result"
  | "progress"
  | "sources"
  | "result"
  | "error"
  | "session"
  | "done";

export interface StreamEvent {
  type: StreamEventType;
  source: string;
  stage: string;
  content: string;
  metadata: Record<string, unknown>;
  session_id?: string;
  turn_id?: string;
  seq?: number;
  timestamp: number;
}

// ---- Client message ----

export interface StartTurnMessage {
  type: "message" | "start_turn";
  content: string;
  tools?: string[];
  capability?: string | null;
  knowledge_bases?: string[];
  session_id?: string | null;
  attachments?: {
    type: string;
    url?: string;
    base64?: string;
    filename?: string;
    mime_type?: string;
  }[];
  language?: string;
  config?: Record<string, unknown>;
  notebook_references?: {
    notebook_id: string;
    record_ids: string[];
  }[];
  history_references?: string[];
}

export interface SubscribeTurnMessage {
  type: "subscribe_turn";
  turn_id: string;
  after_seq?: number;
}

export interface SubscribeSessionMessage {
  type: "subscribe_session";
  session_id: string;
  after_seq?: number;
}

export interface ResumeTurnMessage {
  type: "resume_from";
  turn_id: string;
  seq?: number;
}

export interface UnsubscribeMessage {
  type: "unsubscribe";
  turn_id?: string;
  session_id?: string;
}

export interface CancelTurnMessage {
  type: "cancel_turn";
  turn_id: string;
}

export type ChatMessage =
  | StartTurnMessage
  | SubscribeTurnMessage
  | SubscribeSessionMessage
  | ResumeTurnMessage
  | UnsubscribeMessage
  | CancelTurnMessage;

// ---- Connection manager ----

export type EventHandler = (event: StreamEvent) => void;

export class UnifiedWSClient {
  private ws: WebSocket | null = null;
  private onEvent: EventHandler;
  private onClose?: () => void;
  private _connectPromise: Promise<void> | null = null;
  private _pendingMessages: ChatMessage[] = [];
  private _reconnecting = false;

  constructor(onEvent: EventHandler, onClose?: () => void) {
    this.onEvent = onEvent;
    this.onClose = onClose;
  }

  connect(): void {
    if (this.ws && this.ws.readyState <= WebSocket.OPEN) return;
    this._doConnect();
  }

  private _doConnect(): void {
    const url = wsUrl("/api/v1/ws");
    this.ws = new WebSocket(url);

    this._connectPromise = new Promise<void>((resolve, reject) => {
      const ws = this.ws!;

      ws.onopen = () => {
        resolve();
        // Flush any messages that were queued while connecting
        const queued = [...this._pendingMessages];
        this._pendingMessages = [];
        for (const msg of queued) {
          this.send(msg);
        }
      };

      ws.onmessage = (ev) => {
        try {
          const event: StreamEvent = JSON.parse(ev.data);
          this.onEvent(event);
        } catch {
          console.warn("Unparseable WS message:", ev.data);
        }
      };

      ws.onclose = () => {
        this.ws = null;
        this._connectPromise = null;
        reject(new Error("WebSocket closed before open"));
        this.onClose?.();
      };

      ws.onerror = (err) => {
        console.error("WS error:", err);
      };
    });
  }

  /**
   * Wait for the WebSocket to reach OPEN state.
   * Returns a promise that resolves when connected or rejects on failure.
   */
  async waitForConnection(timeoutMs = 10000): Promise<boolean> {
    if (this.connected) return true;

    // If not connecting, start a connection
    if (!this._connectPromise) {
      this.connect();
    }

    if (!this._connectPromise) return false;

    try {
      await Promise.race([
        this._connectPromise,
        new Promise<void>((_, reject) =>
          setTimeout(() => reject(new Error("Connection timeout")), timeoutMs),
        ),
      ]);
      return true;
    } catch {
      return false;
    }
  }

  send(msg: ChatMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      // Queue the message if we're connecting
      if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
        this._pendingMessages.push(msg);
        return;
      }
      console.error("WebSocket not connected");
      return;
    }
    this.ws.send(JSON.stringify(msg));
  }

  disconnect(): void {
    this._pendingMessages = [];
    this._connectPromise = null;
    this.ws?.close();
    this.ws = null;
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get connecting(): boolean {
    return this.ws?.readyState === WebSocket.CONNECTING;
  }
}
