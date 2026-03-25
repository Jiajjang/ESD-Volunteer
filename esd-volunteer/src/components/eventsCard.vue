<script>
export default {
    name: 'eventsCard',
    props: {
        article: {
            type: Object,
            required: true,
        },
    },
}
</script>
<template>
    <div class="card bg-base-100 w-96 shadow-sm">
        <figure>
            <img
                src="https://img.daisyui.com/images/stock/photo-1606107557195-0e29a4b5b4aa.webp"
                alt="Shoes"
            />
        </figure>
        <div class="card-body">
            <h2 class="card-title">{{ event.title }}</h2>
            <div>
                <span></span>
            </div>
            <p>
                {{event.description}}
            </p>
            <div class="card-actions justify-end">
                <button class="btn btn-primary">Register</button>
            </div>
        </div>
    </div>
</template>
