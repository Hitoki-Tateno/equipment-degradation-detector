/**
 * カテゴリツリーを再帰的にたどり、末端ノードだけをフラットなリストで返す。
 * 各エントリにフルパス文字列を付与する。
 *
 * @param {import('../services/api').CategoryNode[]} categories
 * @param {string} parentPath - 親からの累積パス
 * @returns {{ id: number, name: string, path: string }[]}
 */
export function flattenLeafCategories(categories, parentPath = '') {
  const leaves = [];
  for (const cat of categories) {
    const currentPath = parentPath ? `${parentPath} > ${cat.name}` : cat.name;
    if (!cat.children || cat.children.length === 0) {
      leaves.push({ id: cat.id, name: cat.name, path: currentPath });
    } else {
      leaves.push(...flattenLeafCategories(cat.children, currentPath));
    }
  }
  return leaves;
}
