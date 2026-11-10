import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './rhine.css'
import './rhine-motion.css'
import './rhine-responsive.css'
import './workspace.css'

const app = createApp(App)

app.use(router)

app.mount('#app')
