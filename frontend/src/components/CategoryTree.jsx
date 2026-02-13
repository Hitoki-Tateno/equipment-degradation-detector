import React, { useMemo } from 'react';
import { Tree } from 'antd';
import { ApartmentOutlined } from '@ant-design/icons';

function toTreeData(categories) {
  return categories.map((cat) => ({
    key: String(cat.id),
    title: cat.name,
    icon: <ApartmentOutlined />,
    children: cat.children ? toTreeData(cat.children) : [],
  }));
}

function CategoryTree({ categories, onSelect }) {
  const treeData = useMemo(() => toTreeData(categories), [categories]);

  const handleSelect = (selectedKeys) => {
    if (selectedKeys.length > 0) {
      onSelect(Number(selectedKeys[0]));
    }
  };

  return (
    <Tree
      showIcon
      defaultExpandAll
      treeData={treeData}
      onSelect={handleSelect}
    />
  );
}

export default CategoryTree;
