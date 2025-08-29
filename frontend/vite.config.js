import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,                 // 도커 컨테이너에서 0.0.0.0 바인딩
    port: 5173,                 // Vite 기본 포트
    strictPort: true,           // 지정 포트 고정.
    proxy: {
      '/api': {
        target: 'http://backend:8000', // 도커 네트워크의 backend 서비스
        changeOrigin: true,            // Host 헤더 변경
      },
    },
  },
})