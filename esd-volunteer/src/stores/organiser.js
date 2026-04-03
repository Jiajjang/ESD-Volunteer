import { defineStore } from 'pinia'

export const useOrganiserStore = defineStore('organiser', {
    state: () => ({
        organiserId: 11,
    }),
    actions: {
        setOrganiserId(id) {
            this.organiserId = id
        },
    },
})