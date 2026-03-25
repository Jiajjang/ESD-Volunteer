import { createRouter, createWebHistory } from "vue-router";
import EventsView from '@/views/events.vue'
import EventDetailsView from '@/views/eventDetails.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),  // Clean URLs
  routes : [
    {
      path : '/events',
      name: "events",
      component : EventsView,
    },
    {
      path: '/eventDetails/:id',
      name: "eventDetails",
      component : EventDetailsView,
      props : true

    }
  ]
})

export default router