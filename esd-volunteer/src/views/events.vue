<script setup>
import EventsCard from '@/components/eventsCard.vue'
import NavBar from '@/components/navbar.vue'
// Temp data to test
import { ref } from 'vue'
const events = ref([
  {
    id: 1,
    title: 'Tech Conference 2026',
    description: 'Latest AI and cloud trends from top speakers',
    time: '2026-04-15 09:00',
    location: 'Singapore EXPO',
  },
  {
    id: 2,
    title: 'Vue.js Meetup',
    description: 'Hands-on Vue 3 workshop with live coding',
    time: '2026-04-20 18:30',
    location: 'Google Singapore',

  },
  {
    id: 3,
    title: 'Music Festival',
    description: 'Live bands and food stalls all weekend',
    time: '2026-04-25 14:00',
    location: 'Marina Bay Sands',
  },
])
</script>

<template>
  <NavBar />
  <main class="px-6">
    <h1 class="text-3xl py-6 font-bold">Events</h1>
    <div class="grid-cols-4 gap-8 grid">
      <EventsCard v-for="event in events" :key="event.id" :event="event" />
    </div>
  </main>
</template>
