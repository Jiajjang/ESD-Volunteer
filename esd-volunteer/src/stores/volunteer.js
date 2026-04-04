import { defineStore } from 'pinia'

export const useVolunteerStore = defineStore('volunteer', {
    state: () => ({
        volunteerId: 5,
    }),
    actions: {
        setVolunteerId(id) {
            this.volunteerId = id
        },
    },
})