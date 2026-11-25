import assert from 'node:assert/strict'
import { test } from 'node:test'
import { libraryEmptyState, normalizeLibraryScope } from '../src/data/libraryScope.js'

test('root browse defaults to this level, with a distinct explicit whole-library scope', () => {
  assert.equal(normalizeLibraryScope(undefined, null), 'folder')
  assert.equal(normalizeLibraryScope('all', null), 'all')
  assert.equal(normalizeLibraryScope('subtree', null), 'folder')
  assert.equal(normalizeLibraryScope('subtree', 'folder-id'), 'subtree')
  assert.equal(normalizeLibraryScope(['all', 'folder'], null), 'folder')
})

test('an empty root with folders offers the whole library, while filtered results offer reset', () => {
  assert.deepEqual(libraryEmptyState({ scope: 'folder', childCount: 2 }), {
    description: '根目录下没有直接存放的资料。', action: 'all',
  })
  assert.deepEqual(libraryEmptyState({ scope: 'all', filtered: true }), {
    description: '没有符合筛选条件的资料。', action: 'clear',
  })
  assert.deepEqual(libraryEmptyState({ scope: 'all' }), {
    description: '全库还没有资料。', action: 'upload',
  })
  assert.deepEqual(libraryEmptyState({ scope: 'subtree', folderId: 'folder-id' }), {
    description: '此目录和子目录中还没有资料。', action: 'upload',
  })
})
