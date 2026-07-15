<script lang="ts">
	import { onMount } from 'svelte';
	import { getShowcase } from '$lib/apis/images';

	let images: { id: string; url: string; user_name: string; filename: string }[] = [];
	let loading = true;

	onMount(async () => {
		try {
			images = await getShowcase();
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>优秀作品展示</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
	<h1 class="text-2xl font-bold text-center mb-6 text-gray-800 dark:text-gray-100">
		优秀作品展示
	</h1>

	{#if loading}
		<p class="text-center text-gray-500">加载中...</p>
	{:else if images.length === 0}
		<p class="text-center text-gray-400">暂无精选作品</p>
	{:else}
		<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 max-w-6xl mx-auto">
			{#each images as img}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
					<img
						src={img.url}
						alt="generated"
						class="w-full h-48 object-cover"
						loading="lazy"
					/>
					<div class="p-2 text-sm text-gray-500 dark:text-gray-400">
						作者: {img.user_name}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
