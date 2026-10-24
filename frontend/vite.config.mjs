import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins:[react()],
  define:{'process.env.REACT_APP_API_URL':JSON.stringify(process.env.REACT_APP_API_URL || '/api/v1')},
  build:{outDir:'build',chunkSizeWarningLimit:700},
  server:{proxy:{'/api':{target:'http://127.0.0.1:8000',ws:true}}},
  test:{environment:'jsdom',globals:true,maxWorkers:1,include:['src/**/*.test.{js,jsx}']}
});
