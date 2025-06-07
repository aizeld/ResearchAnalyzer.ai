import { createRouter, createWebHistory } from 'vue-router';
import MainView from '../views/HomeView.vue';
import FilesView from '../views/FilesView.vue';
import PdfView from '../views/PdfView.vue';
import RegistrationView from '../views/RegistrationView.vue';
import LoginView from '../views/LoginView.vue';
const routes = [
    

      {
        path: '/',
        name: 'Main',
        component: MainView,
       
      },

      {
        path: '/files',
        name: 'Files',
        component: FilesView,
       
      },
      {
        path: '/files/:filePath',
        name: 'PdfExplorerView',
        component: PdfView,
        props: true,
      },
      {
        'path': '/register',
        name: 'RegistrationView',
        component: RegistrationView
      }
      ,
      {
        'path': '/login',
        name: 'LoginView',
        component: LoginView      },

]

const BASE_URL = '/';

const router = createRouter({
  history: createWebHistory(BASE_URL),
  routes
})




export default router