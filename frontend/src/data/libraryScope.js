export function normalizeLibraryScope(scope, folderId) {
  if (scope === 'all' || (scope === 'subtree' && folderId)) return scope
  return 'folder'
}

export function libraryEmptyState({ scope, folderId, filtered, childCount }) {
  if (filtered) return { description: '没有符合筛选条件的资料。', action: 'clear' }
  if (scope === 'all') return { description: '全库还没有资料。', action: 'upload' }
  if (scope === 'subtree') return { description: '此目录和子目录中还没有资料。', action: 'upload' }
  return {
    description: folderId ? '当前目录下没有直接存放的资料。' : '根目录下没有直接存放的资料。',
    action: childCount ? 'all' : 'upload',
  }
}
