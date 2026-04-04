import { createRouter, createWebHistory } from "vue-router";
import EventsView from '@/views/events.vue'
import EventDetailsView from '@/views/eventDetails.vue'
import VolunteerView from '@/views/volunteer.vue'
import OrganiserView from '@/views/organiser.vue'
import LoginView from '@/views/login.vue'

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

    },
    {
      path : '/volunteer',
      name: "volunteer",
      component: VolunteerView
    },
    {
      path : '/organiser',
      name: "organiser",
      component: OrganiserView
    },
    {
      path : '/',
      name: "login",
      component: LoginView
    },
  ]
})

export default router