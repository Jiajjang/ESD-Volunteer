import { createRouter, createWebHistory } from "vue-router";

import EventsView from '@/views/events.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),  // Clean URLs
  routes : [
    {
      path : '/',
      name: "events",
      component : EventsView,
      // meta : {requiresAuth: false}
    }
  ]
})

export default router