import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import MapView from '../views/MapView.vue'
import MonitorView from '../views/MonitorView.vue'
import PlanView from '../views/PlanView.vue'
import ActView from '../views/ActView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/map', name: 'map', component: MapView },
  { path: '/monitor', name: 'monitor', component: MonitorView },
  { path: '/plan', name: 'plan', component: PlanView },
  { path: '/act', name: 'act', component: ActView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
