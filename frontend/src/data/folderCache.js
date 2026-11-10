// One cache per mounted library view: no data survives an account/route teardown.
export function createFolderCache(fetchFolders,{ttlMs=30_000,now=Date.now}={}) {
  const entries=new Map()
  function load(parent) {
    const key=parent??null,existing=entries.get(key)
    if(existing&&(existing.pending||existing.expires>now()))return existing.promise
    const entry={pending:true,expires:0,promise:null}
    entry.promise=Promise.resolve().then(()=>fetchFolders(parent)).then(value=>{
      entry.pending=false;entry.expires=now()+ttlMs
      return value
    },error=>{
      if(entries.get(key)===entry)entries.delete(key)
      throw error
    })
    entries.set(key,entry)
    return entry.promise
  }
  return {load,clear(){entries.clear()}}
}
