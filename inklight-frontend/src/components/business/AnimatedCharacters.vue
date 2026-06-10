<template>
  <div ref="containerRef" class="characters-container">
    <!-- Purple character -->
    <div
      ref="purpleRef"
      class="character purple"
      :style="{ height: purpleHeight + 'px' }"
    >
      <div ref="purpleFaceRef" class="face purple-face">
        <div class="eyeball" data-max-distance="5">
          <div class="eyeball-pupil"></div>
        </div>
        <div class="eyeball" data-max-distance="5">
          <div class="eyeball-pupil"></div>
        </div>
      </div>
    </div>

    <!-- Black character -->
    <div ref="blackRef" class="character black">
      <div ref="blackFaceRef" class="face black-face">
        <div class="eyeball" data-max-distance="4">
          <div class="eyeball-pupil"></div>
        </div>
        <div class="eyeball" data-max-distance="4">
          <div class="eyeball-pupil"></div>
        </div>
      </div>
    </div>

    <!-- Orange character (front) -->
    <div ref="orangeRef" class="character orange">
      <div ref="orangeFaceRef" class="face orange-face">
        <div class="pupil" data-max-distance="5"></div>
        <div class="pupil" data-max-distance="5"></div>
      </div>
    </div>

    <!-- Yellow character (frontmost) -->
    <div ref="yellowRef" class="character yellow">
      <div ref="yellowFaceRef" class="face yellow-face">
        <div class="pupil" data-max-distance="5"></div>
        <div class="pupil" data-max-distance="5"></div>
      </div>
      <div ref="yellowMouthRef" class="yellow-mouth"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps<{
  isTyping?: boolean
  showPassword?: boolean
  passwordLength?: number
}>()

const containerRef = ref<HTMLElement | null>(null)
const purpleRef = ref<HTMLElement | null>(null)
const blackRef = ref<HTMLElement | null>(null)
const yellowRef = ref<HTMLElement | null>(null)
const orangeRef = ref<HTMLElement | null>(null)
const purpleFaceRef = ref<HTMLElement | null>(null)
const blackFaceRef = ref<HTMLElement | null>(null)
const yellowFaceRef = ref<HTMLElement | null>(null)
const orangeFaceRef = ref<HTMLElement | null>(null)
const yellowMouthRef = ref<HTMLElement | null>(null)

const purpleHeight = ref(400)

// Mouse tracking
const mouse = { x: 0, y: 0 }
let rafId = 0
let isLooking = false
let lookingTimer: ReturnType<typeof setTimeout> | undefined
let purpleBlinkTimer: ReturnType<typeof setTimeout> | undefined
let blackBlinkTimer: ReturnType<typeof setTimeout> | undefined
let purplePeekTimer: ReturnType<typeof setTimeout> | undefined

const isHiding = () => props.passwordLength && props.passwordLength > 0 && !props.showPassword
const isShowing = () => props.passwordLength && props.passwordLength > 0 && props.showPassword

// Helpers
function qs(el: HTMLElement, sel: string) {
  return el.querySelectorAll(sel)
}

function setTransform(el: HTMLElement, x: number, y: number) {
  el.style.transform = `translate(${x}px, ${y}px)`
}

function calcPos(el: HTMLElement) {
  const rect = el.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 3
  const dx = mouse.x - cx
  const dy = mouse.y - cy
  return {
    faceX: Math.max(-15, Math.min(15, dx / 20)),
    faceY: Math.max(-10, Math.min(10, dy / 30)),
    bodySkew: Math.max(-6, Math.min(6, -dx / 120)),
  }
}

function calcEyePos(el: HTMLElement, maxDist: number) {
  const r = el.getBoundingClientRect()
  const cx = r.left + r.width / 2
  const cy = r.top + r.height / 2
  const dx = mouse.x - cx
  const dy = mouse.y - cy
  const dist = Math.min(Math.sqrt(dx * dx + dy * dy), maxDist)
  const angle = Math.atan2(dy, dx)
  return { x: Math.cos(angle) * dist, y: Math.sin(angle) * dist }
}

function schedulePurpleBlink() {
  if (!purpleRef.value) return
  const ebs = qs(purpleRef.value, '.eyeball')
  if (!ebs.length) return

  purpleBlinkTimer = setTimeout(() => {
    ebs.forEach((el) => {
      (el as HTMLElement).style.height = '2px'
    })
    setTimeout(() => {
      ebs.forEach((el) => {
        (el as HTMLElement).style.height = ''
      })
      schedulePurpleBlink()
    }, 150)
  }, Math.random() * 4000 + 3000)
}

function scheduleBlackBlink() {
  if (!blackRef.value) return
  const ebs = qs(blackRef.value, '.eyeball')
  if (!ebs.length) return

  blackBlinkTimer = setTimeout(() => {
    ebs.forEach((el) => {
      (el as HTMLElement).style.height = '2px'
    })
    setTimeout(() => {
      ebs.forEach((el) => {
        (el as HTMLElement).style.height = ''
      })
      scheduleBlackBlink()
    }, 150)
  }, Math.random() * 4000 + 3000)
}

function schedulePurplePeek() {
  if (!purpleRef.value) return
  const pupils = qs(purpleRef.value, '.eyeball-pupil')
  if (!pupils.length) return

  purplePeekTimer = setTimeout(() => {
    pupils.forEach((p) => { setTransform(p as HTMLElement, 4, 5) })
    if (purpleFaceRef.value) {
      purpleFaceRef.value.style.left = '20px'
      purpleFaceRef.value.style.top = '35px'
    }
    setTimeout(() => {
      pupils.forEach((p) => { setTransform(p as HTMLElement, -4, -4) })
      schedulePurplePeek()
    }, 800)
  }, Math.random() * 3000 + 2000)
}

function applyLookAtEachOther() {
  if (purpleFaceRef.value) {
    purpleFaceRef.value.style.left = '55px'
    purpleFaceRef.value.style.top = '65px'
  }
  if (blackFaceRef.value) {
    blackFaceRef.value.style.left = '32px'
    blackFaceRef.value.style.top = '12px'
  }
  if (purpleRef.value) {
    qs(purpleRef.value, '.eyeball-pupil').forEach((p) => setTransform(p as HTMLElement, 3, 4))
  }
  if (blackRef.value) {
    qs(blackRef.value, '.eyeball-pupil').forEach((p) => setTransform(p as HTMLElement, 0, -4))
  }
}

function applyHidingPassword() {
  if (purpleFaceRef.value) {
    purpleFaceRef.value.style.left = '55px'
    purpleFaceRef.value.style.top = '65px'
  }
}

function applyShowPassword() {
  if (purpleRef.value) {
    purpleRef.value.style.transform = ''
    purpleHeight.value = 400
  }
  if (blackRef.value) blackRef.value.style.transform = ''
  if (orangeRef.value) orangeRef.value.style.transform = ''
  if (yellowRef.value) yellowRef.value.style.transform = ''

  if (purpleFaceRef.value) {
    purpleFaceRef.value.style.left = '20px'
    purpleFaceRef.value.style.top = '35px'
  }
  if (blackFaceRef.value) {
    blackFaceRef.value.style.left = '10px'
    blackFaceRef.value.style.top = '28px'
  }
  if (orangeFaceRef.value) {
    orangeFaceRef.value.style.left = '82px'
    orangeFaceRef.value.style.top = '90px'
  }
  if (yellowFaceRef.value) {
    yellowFaceRef.value.style.left = '52px'
    yellowFaceRef.value.style.top = '40px'
  }
  if (yellowMouthRef.value) {
    yellowMouthRef.value.style.left = '40px'
    yellowMouthRef.value.style.top = '88px'
  }

  if (purpleRef.value) {
    qs(purpleRef.value, '.eyeball-pupil').forEach((p) => setTransform(p as HTMLElement, -4, -4))
  }
  if (blackRef.value) {
    qs(blackRef.value, '.eyeball-pupil').forEach((p) => setTransform(p as HTMLElement, -4, -4))
  }
  if (orangeRef.value) {
    qs(orangeRef.value, '.pupil').forEach((p) => setTransform(p as HTMLElement, -5, -4))
  }
  if (yellowRef.value) {
    qs(yellowRef.value, '.pupil').forEach((p) => setTransform(p as HTMLElement, -5, -4))
  }
}

function tick() {
  const container = containerRef.value
  if (!container) return

  const typing = props.isTyping
  const hiding = isHiding()
  const showing = isShowing()
  const looking = isLooking

  if (purpleRef.value && !showing) {
    const pp = calcPos(purpleRef.value)
    if (typing || hiding) {
      purpleRef.value.style.transform = `translate(${40}px, 0) skewX(${pp.bodySkew - 12}deg)`
      purpleHeight.value = 440
    } else {
      purpleRef.value.style.transform = `translate(0, 0) skewX(${pp.bodySkew}deg)`
      purpleHeight.value = 400
    }
  }

  if (blackRef.value && !showing) {
    const bp = calcPos(blackRef.value)
    if (looking) {
      blackRef.value.style.transform = `translateX(${20}px) skewX(${bp.bodySkew * 1.5 + 10}deg)`
    } else if (typing || hiding) {
      blackRef.value.style.transform = `translateX(0) skewX(${bp.bodySkew * 1.5}deg)`
    } else {
      blackRef.value.style.transform = `translateX(0) skewX(${bp.bodySkew}deg)`
    }
  }

  if (orangeRef.value && !showing) {
    const op = calcPos(orangeRef.value)
    orangeRef.value.style.transform = `skewX(${op.bodySkew}deg)`
  }

  if (yellowRef.value && !showing) {
    const yp = calcPos(yellowRef.value)
    yellowRef.value.style.transform = `skewX(${yp.bodySkew}deg)`
  }

  if (purpleRef.value && !showing && !looking) {
    const pp = calcPos(purpleRef.value)
    const faceX = pp.faceX >= 0 ? Math.min(25, pp.faceX * 1.5) : pp.faceX
    if (purpleFaceRef.value) {
      purpleFaceRef.value.style.left = (45 + faceX) + 'px'
      purpleFaceRef.value.style.top = (40 + pp.faceY) + 'px'
    }
  }

  if (blackRef.value && !showing && !looking) {
    const bp = calcPos(blackRef.value)
    if (blackFaceRef.value) {
      blackFaceRef.value.style.left = (26 + bp.faceX) + 'px'
      blackFaceRef.value.style.top = (32 + bp.faceY) + 'px'
    }
  }

  if (orangeRef.value && !showing) {
    const op = calcPos(orangeRef.value)
    if (orangeFaceRef.value) {
      orangeFaceRef.value.style.left = (82 + op.faceX) + 'px'
      orangeFaceRef.value.style.top = (90 + op.faceY) + 'px'
    }
  }

  if (yellowRef.value && !showing) {
    const yp = calcPos(yellowRef.value)
    if (yellowFaceRef.value) {
      yellowFaceRef.value.style.left = (52 + yp.faceX) + 'px'
      yellowFaceRef.value.style.top = (40 + yp.faceY) + 'px'
    }
  }

  if (yellowRef.value && !showing) {
    const yp = calcPos(yellowRef.value)
    if (yellowMouthRef.value) {
      yellowMouthRef.value.style.left = (40 + yp.faceX) + 'px'
      yellowMouthRef.value.style.top = (88 + yp.faceY) + 'px'
    }
  }

  if (!showing) {
    const allPupils = qs(container, '.pupil')
    allPupils.forEach((p) => {
      const el = p as HTMLElement
      const maxDist = Number(el.dataset.maxDistance) || 5
      const ePos = calcEyePos(el, maxDist)
      setTransform(el, ePos.x, ePos.y)
    })

    if (!looking) {
      const allEyeballs = qs(container, '.eyeball')
      allEyeballs.forEach((eb) => {
        const el = eb as HTMLElement
        const maxDist = Number(el.dataset.maxDistance) || 10
        const pupil = el.querySelector('.eyeball-pupil') as HTMLElement
        if (!pupil) return
        const ePos = calcEyePos(el, maxDist)
        setTransform(pupil, ePos.x || 0, ePos.y || 0)
      })
    }
  }

  rafId = requestAnimationFrame(tick)
}

function onMouseMove(e: MouseEvent) {
  mouse.x = e.clientX
  mouse.y = e.clientY
}

// Watch isTyping
watch(() => props.isTyping, (typing) => {
  if (typing && !props.showPassword) {
    isLooking = true
    applyLookAtEachOther()
    clearTimeout(lookingTimer)
    lookingTimer = setTimeout(() => {
      isLooking = false
    }, 800)
  } else {
    clearTimeout(lookingTimer)
    isLooking = false
  }
})

watch([() => props.showPassword, () => props.passwordLength], ([showPw]) => {
  if (showPw) {
    applyShowPassword()
  } else if (isHiding()) {
    applyHidingPassword()
  }
}, { immediate: false })

onMounted(() => {
  window.addEventListener('mousemove', onMouseMove, { passive: true })
  rafId = requestAnimationFrame(tick)
  schedulePurpleBlink()
  scheduleBlackBlink()
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  cancelAnimationFrame(rafId)
  clearTimeout(purpleBlinkTimer)
  clearTimeout(blackBlinkTimer)
  clearTimeout(purplePeekTimer)
  clearTimeout(lookingTimer)
})
</script>

<style scoped>
.characters-container {
  position: relative;
  width: 550px;
  height: 450px;
}

.character {
  position: absolute;
  bottom: 0;
  transform-origin: bottom center;
  will-change: transform;
  transition: height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ─── Purple ─── */
.character.purple {
  left: 70px;
  width: 180px;
  height: 400px;
  background: #6C3FF5;
  border-radius: 10px 10px 0 0;
  z-index: 1;
}

.purple-face {
  position: absolute;
  display: flex;
  gap: 32px;
  left: 45px;
  top: 40px;
}

.purple-face .eyeball {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  will-change: height;
  transition: height 0.08s ease;
}

.purple-face .eyeball-pupil {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #2D2D2D;
  will-change: transform;
}

/* ─── Black ─── */
.character.black {
  left: 240px;
  width: 120px;
  height: 310px;
  background: #2D2D2D;
  border-radius: 8px 8px 0 0;
  z-index: 2;
}

.black-face {
  position: absolute;
  display: flex;
  gap: 24px;
  left: 26px;
  top: 32px;
}

.black-face .eyeball {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  will-change: height;
  transition: height 0.08s ease;
}

.black-face .eyeball-pupil {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2D2D2D;
  will-change: transform;
}

/* ─── Orange ─── */
.character.orange {
  left: 0;
  width: 240px;
  height: 200px;
  background: #FF9B6B;
  border-radius: 120px 120px 0 0;
  z-index: 3;
}

.orange-face {
  position: absolute;
  display: flex;
  gap: 32px;
  left: 82px;
  top: 90px;
}

.orange-face .pupil {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #2D2D2D;
  will-change: transform;
}

/* ─── Yellow (front) ─── */
.character.yellow {
  left: 310px;
  width: 140px;
  height: 230px;
  background: #E8D754;
  border-radius: 70px 70px 0 0;
  z-index: 4;
}

.yellow-face {
  position: absolute;
  display: flex;
  gap: 24px;
  left: 52px;
  top: 40px;
}

.yellow-face .pupil {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #2D2D2D;
  will-change: transform;
}

.yellow-mouth {
  position: absolute;
  width: 80px;
  height: 4px;
  background: #2D2D2D;
  border-radius: 9999px;
  left: 40px;
  top: 88px;
  will-change: transform;
}

/* Face position transitions */
.face {
  transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              top 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.yellow-mouth {
  transition: left 0.2s cubic-bezier(0.4, 0, 0.2, 1),
              top 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Character body transitions */
.character {
  transition: height 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Circle follow transitions */
.pupil,
.eyeball-pupil {
  transition: transform 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
