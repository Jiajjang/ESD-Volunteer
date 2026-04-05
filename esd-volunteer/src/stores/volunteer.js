import { defineStore } from 'pinia'
import { useLocalStorage } from '@vueuse/core'

export const useVolunteerStore = defineStore('volunteer', {
    state: () => ({
        volunteerId: useLocalStorage('volunteerId', null),
    }),
    actions: {
        setVolunteerId(id) {
            this.volunteerId = id
        },
        clearVolunteerId() {
            this.volunteerId = null
        },
    },
})