import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import VueCookies from 'vue3-cookies';
import router from './router';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min.js';


const app = createApp(App)


app.use(VueCookies)

app.use(router);


app.mount('#app')