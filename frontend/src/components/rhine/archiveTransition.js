import { shallowReactive } from 'vue'
// Only ephemeral presentation state. No credentials, snapshots, or document data.
export const archiveTransition = shallowReactive({ active:false, frameStyle:{opacity:0}, corners:0, cornerScale:1, shade:0, captionStyle:{opacity:0} })
export function resetArchiveTransition() {
  Object.assign(archiveTransition,{active:false,frameStyle:{opacity:0},corners:0,cornerScale:1,shade:0,captionStyle:{opacity:0}})
}
