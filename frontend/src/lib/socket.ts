import { io, Socket } from "socket.io-client";
import { getAccessToken } from "./auth";

let socket: Socket | null = null;

export function connectSocket(): Socket {
  if (socket?.connected) return socket;

  socket = io({
    path: "/ws/socket.io",
    auth: { token: getAccessToken() },
    transports: ["websocket"],
  });

  return socket;
}

export function getSocket(): Socket | null {
  return socket;
}

export function disconnectSocket(): void {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}
