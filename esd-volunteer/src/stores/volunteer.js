import { defineStore } from 'pinia'

export const useVolunteerStore = defineStore('volunteer', {
    state: () => ({
        volunteerId: 24,
    }),
    actions: {
        setVolunteerId(id) {
            this.volunteerId = id
        },
    },
})