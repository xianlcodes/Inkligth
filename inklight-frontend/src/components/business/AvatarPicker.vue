<template>
  <div class="avatar-picker">
    <div class="avatar-preview">
      <img :src="previewUrl" alt="头像预览" class="preview-img" />
    </div>
    <div class="style-grid">
      <div
        v-for="style in stylePreviews"
        :key="style.name"
        :class="['style-card', { active: selectedStyle === style.name }]"
        @click="selectStyle(style.name)"
      >
        <img :src="style.previewUrl" :alt="style.label" class="style-img" />
        <span class="style-label">{{ style.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const props = defineProps<{
  modelValue: string | null
  username: string
  email: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const seed = computed(() => props.username || props.email || 'user')

const styles = [
  { name: 'initials', label: '字母' },
  { name: 'avataaars', label: '卡通' },
  { name: 'bottts', label: '机器人' },
  { name: 'pixel-art', label: '像素' },
  { name: 'lorelei', label: '简约' },
  { name: 'notionists', label: '涂鸦' },
  { name: 'thumbs', label: '拇指' },
  { name: 'fun-emoji', label: '表情' },
  { name: 'shapes', label: '几何' },
  { name: 'identicon', label: '对称' },
]

const selectedStyle = ref(props.modelValue || 'initials')

const previewUrl = computed(() => {
  const style = selectedStyle.value || 'initials'
  return `https://api.dicebear.com/9.x/${style}/svg?seed=${encodeURIComponent(seed.value)}`
})

const stylePreviews = computed(() =>
  styles.map((s) => ({
    ...s,
    previewUrl: `https://api.dicebear.com/9.x/${s.name}/svg?seed=${encodeURIComponent(seed.value)}`,
  }))
)

function selectStyle(name: string) {
  selectedStyle.value = name
  emit('update:modelValue', name)
}

watch(
  () => props.modelValue,
  (val) => {
    if (val) selectedStyle.value = val
  }
)
</script>

<style scoped>
.avatar-picker {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.avatar-preview {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  overflow: hidden;
  border: 3px solid var(--accent-primary);
  box-shadow: 0 4px 12px rgba(13, 148, 136, 0.2);
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.style-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  width: 100%;
}

.style-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 6px;
  border-radius: var(--radius-md);
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--bg-secondary);
}

.style-card:hover {
  border-color: var(--teal-300);
  background: var(--bg-primary);
}

.style-card.active {
  border-color: var(--accent-primary);
  background: rgba(13, 148, 136, 0.08);
}

.style-img {
  width: 48px;
  height: 48px;
  border-radius: 50%;
}

.style-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.style-card.active .style-label {
  color: var(--accent-primary);
  font-weight: 600;
}
</style>