import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { Markdown, type MarkdownStorage } from 'tiptap-markdown'
import { useEffect } from 'react'

interface Props {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export default function RichTextEditor({ value, onChange, placeholder }: Props) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Markdown,
      Placeholder.configure({ placeholder: placeholder ?? 'Write your instructions…' }),
    ],
    content: value,
    onUpdate({ editor }) {
      onChange((editor.storage as unknown as { markdown: MarkdownStorage }).markdown.getMarkdown())
    },
  })

  useEffect(() => {
    if (!editor || editor.isDestroyed) return
    const current = (editor.storage as unknown as { markdown: MarkdownStorage }).markdown.getMarkdown()
    if (value !== current) {
      editor.commands.setContent(value)
    }
  }, [value, editor])

  return (
    <div className="pa-rte">
      <div className="pa-rte-toolbar">
        <button
          type="button"
          title="Bold"
          className={editor?.isActive('bold') ? 'active' : ''}
          onClick={() => editor?.chain().focus().toggleBold().run()}
        >
          <strong>B</strong>
        </button>
        <button
          type="button"
          title="Italic"
          className={editor?.isActive('italic') ? 'active' : ''}
          onClick={() => editor?.chain().focus().toggleItalic().run()}
        >
          <em>I</em>
        </button>
        <div className="pa-rte-toolbar-sep" />
        <button
          type="button"
          title="Heading"
          className={editor?.isActive('heading', { level: 2 }) ? 'active' : ''}
          onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
        >
          H2
        </button>
        <button
          type="button"
          title="Subheading"
          className={editor?.isActive('heading', { level: 3 }) ? 'active' : ''}
          onClick={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()}
        >
          H3
        </button>
        <div className="pa-rte-toolbar-sep" />
        <button
          type="button"
          title="Bullet list"
          className={editor?.isActive('bulletList') ? 'active' : ''}
          onClick={() => editor?.chain().focus().toggleBulletList().run()}
        >
          • List
        </button>
        <button
          type="button"
          title="Numbered list"
          className={editor?.isActive('orderedList') ? 'active' : ''}
          onClick={() => editor?.chain().focus().toggleOrderedList().run()}
        >
          1. List
        </button>
        <div className="pa-rte-toolbar-sep" />
        <button
          type="button"
          title="Insert a step break (separates steps in Cook Mode)"
          className="pa-rte-add-step"
          onClick={() => editor?.chain().focus().setHorizontalRule().run()}
        >
          + Add Step
        </button>
      </div>
      <EditorContent editor={editor} className="pa-rte-content" />
    </div>
  )
}
