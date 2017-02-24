# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.buffer_manager
import app.controller
import app.cu_editor
import app.editor
import app.history
import app.text_buffer
import sys
import curses


class StaticWindow:
  """A static window does not get focus.
  parent is responsible for the order in which this window is updated, relative
  to its siblings."""
  def __init__(self, parent):
    self.parent = parent
    self.zOrder = []
    self.color = 0
    self.colorSelected = 1
    self.isFocusable = False
    self.top = 0
    self.left = 0
    self.rows = 1
    self.cols = 1
    self.writeLineRow = 0
    self.cursorWindow = curses.newwin(1, 1)
    self.cursorWindow.leaveok(1)  # Don't update cursor position.
    self.cursorWindow.timeout(10)

  def addStr(self, row, col, text, colorPair):
    """Overwrite text a row, column with text."""
    try: self.cursorWindow.addstr(row, col, text, colorPair)
    except curses.error: pass

  def changeFocusTo(self, changeTo):
    self.parent.changeFocusTo(changeTo)

  def paint(self, row, col, count, colorPair):
    """Paint text a row, column with colorPair.
      fyi, I thought this may be faster than using addStr to paint over the text
      with a different colorPair. It looks like there isn't a significant
      performance difference between chgat and addstr."""
    self.cursorWindow.chgat(row, col, count, colorPair)

  def blank(self):
    """Clear the window."""
    for i in range(self.rows):
      self.addStr(i, 0, ' '*self.cols, self.color)
    self.cursorWindow.refresh()

  def contains(self, row, col):
    """Determine whether the position at row, col lay within this window."""
    for i in self.zOrder:
      if i.contains(row, col):
        return i
    return (self.top <= row < self.top+self.rows and
        self.left <= col < self.left + self.cols and self)

  def debugDraw(self, win):
    self.parent.debugDraw(win)

  def hide(self):
    """Remove window from the render list."""
    try: self.parent.zOrder.remove(self)
    except ValueError: app.log.detail(repr(self)+'not found in zOrder')

  def mouseClick(self, row, col, shift, ctrl, alt):
    pass

  def mouseDoubleClick(self, row, col, shift, ctrl, alt):
    pass

  def mouseMoved(self, row, col, shift, ctrl, alt):
    pass

  def mouseRelease(self, row, col, shift, ctrl, alt):
    pass

  def mouseTripleClick(self, row, col, shift, ctrl, alt):
    pass

  def mouseWheelDown(self, shift, ctrl, alt):
    pass

  def mouseWheelUp(self, shift, ctrl, alt):
    pass

  def moveTo(self, top, left):
    app.log.detail('move', top, left)
    if top == self.top and left == self.left:
      return
    self.top = top
    self.left = left
    try:
      self.cursorWindow.mvwin(self.top, self.left)
    except:
      app.log.info('error mvwin', top, left, repr(self))
      app.log.detail('error mvwin', top, left, repr(self))

  def moveBy(self, top, left):
    app.log.detail('moveBy', top, left, repr(self))
    if top == 0 and left == 0:
      return
    self.top += top
    self.left += left
    self.cursorWindow.mvwin(self.top, self.left)

  def refresh(self):
    """Redraw window."""
    self.cursorWindow.refresh()
    for child in reversed(self.zOrder):
      child.refresh()

  def reshape(self, rows, cols, top, left):
    self.moveTo(top, left)
    self.resizeTo(rows, cols)

  def resizeTo(self, rows, cols):
    app.log.detail('resizeTo', rows, cols)
    self.rows = rows
    self.cols = cols
    try:
      self.cursorWindow.resize(self.rows, self.cols)
    except:
      app.log.detail('resize failed', self.rows, self.cols)

  def resizeBy(self, rows, cols):
    app.log.detail('resizeBy', rows, cols, repr(self))
    self.rows += rows
    self.cols += cols
    if self.rows <= 0 or self.cols <= 0:
      return
    self.cursorWindow.resize(self.rows, self.cols)

  def resizeTopBy(self, rows):
    app.log.detail('resizeTopBy', rows, repr(self))
    self.top += rows
    self.rows -= rows
    if self.rows <= 0:
      return
    self.cursorWindow.resize(self.rows, self.cols)
    self.cursorWindow.mvwin(self.top, self.left)

  def setParent(self, parent, layerIndex):
    if self.parent:
      try: self.parent.zOrder.remove(self)
      except: pass
    self.parent = parent
    if parent:
      self.parent.zOrder.insert(layerIndex, self)

  def show(self):
    """Show window and bring it to the top layer."""
    try: self.parent.zOrder.remove(self)
    except: pass
    self.parent.zOrder.append(self)

  def writeLine(self, text, colorPair=1):
    """Simple line writer for static windows."""
    text = str(text)[:self.cols]
    text = text + ' '*max(0, self.cols-len(text))
    try: self.cursorWindow.addstr(self.writeLineRow, 0, text,
        curses.color_pair(colorPair))
    except curses.error: pass
    self.writeLineRow += 1


class Window(StaticWindow):
  """A Window may have focus. A Window holds a TextBuffer and a
    controller that operates on the TextBuffer."""
  def __init__(self, parent, controller=None):
    StaticWindow.__init__(self, parent)
    self.controller = controller
    self.cursorWindow.keypad(1)
    self.hasFocus = False
    self.isFocusable = True
    self.textBuffer = None

  def focus(self):
    app.log.info('focus', self)
    self.hasFocus = True
    try: self.parent.zOrder.remove(self)
    except ValueError: app.log.detail(repr(self)+'not found in zOrder')
    self.parent.zOrder.append(self)
    self.cursorWindow.leaveok(0)  # Do update cursor position.
    self.controller.focus()

  def mouseClick(self, row, col, shift, ctrl, alt):
    self.textBuffer.mouseClick(row, col, shift, ctrl, alt)

  def mouseDoubleClick(self, row, col, shift, ctrl, alt):
    self.textBuffer.mouseDoubleClick(row, col, shift, ctrl, alt)

  def mouseMoved(self, row, col, shift, ctrl, alt):
    self.textBuffer.mouseMoved(row, col, shift, ctrl, alt)

  def mouseRelease(self, row, col, shift, ctrl, alt):
    self.textBuffer.mouseRelease(row, col, shift, ctrl, alt)

  def mouseTripleClick(self, row, col, shift, ctrl, alt):
    self.textBuffer.mouseTripleClick(row, col, shift, ctrl, alt)

  def mouseWheelDown(self, shift, ctrl, alt):
    self.textBuffer.mouseWheelDown(shift, ctrl, alt)

  def mouseWheelUp(self, shift, ctrl, alt):
    self.textBuffer.mouseWheelUp(shift, ctrl, alt)

  def refresh(self):
    StaticWindow.refresh(self)
    self.textBuffer.draw(self)
    if self.hasFocus:
      self.parent.debugDraw(self)
      try:
        self.cursorWindow.move(
            self.textBuffer.cursorRow - self.textBuffer.scrollRow,
            self.textBuffer.cursorCol - self.textBuffer.scrollCol)
      except curses.error:
        pass

  def setTextBuffer(self, textBuffer):
    textBuffer.setView(self)
    self.textBuffer = textBuffer

  def unfocus(self):
    app.log.info('unfocus', self)
    self.hasFocus = False
    self.cursorWindow.leaveok(1)  # Don't update cursor position.
    self.controller.unfocus()
    #assert(self.prg.exiting or self.prg.changeTo)


class HeaderLine(StaticWindow):
  def __init__(self, parent, host):
    StaticWindow.__init__(self, parent)
    self.host = host
    self.textLine = None

  def refresh(self):
    textLine = self.host.textBuffer.fullPath
    if self.textLine == textLine:
      return
    self.textLine = textLine
    self.blank()
    self.addStr(0, 0, textLine, self.color)
    self.cursorWindow.refresh()


class FileListPanel(Window):
  def __init__(self, parent):
    Window.__init__(self, parent)
    self.color = curses.color_pair(18)
    self.colorSelected = curses.color_pair(3)


class LabeledLine(Window):
  def __init__(self, parent, label):
    Window.__init__(self, parent)
    self.host = parent
    self.setTextBuffer(app.text_buffer.TextBuffer())
    self.label = label
    self.leftColumn = StaticWindow(self)

  def refresh(self):
    self.leftColumn.addStr(0, 0, self.label, self.color)
    self.leftColumn.cursorWindow.refresh()
    Window.refresh(self)

  def reshape(self, rows, cols, top, left):
    labelWidth = len(self.label)
    Window.reshape(self, rows, cols-labelWidth, top, left+labelWidth)
    self.leftColumn.reshape(rows, labelWidth, top, left)

  def unfocus(self):
    self.blank()
    self.hide()
    self.leftColumn.blank()
    self.leftColumn.hide()
    Window.unfocus(self)


class InteractiveFind(LabeledLine):
  def __init__(self, host):
    LabeledLine.__init__(self, host, "find: ")
    self.controller = app.cu_editor.InteractiveFind(host,
        self.textBuffer)


class InteractiveGoto(LabeledLine):
  def __init__(self, parent, host):
    LabeledLine.__init__(self, parent, "goto: ")
    self.controller = app.cu_editor.InteractiveGoto(host,
        self.textBuffer)


class InteractiveOpener(LabeledLine):
  def __init__(self, prg, host):
    LabeledLine.__init__(self, host, "file: ")
    self.fileListing = app.text_buffer.TextBuffer()
    self.controller = app.cu_editor.InteractiveOpener(prg, host,
        self.textBuffer)


class InteractiveQuit(LabeledLine):
  def __init__(self, parent, host):
    LabeledLine.__init__(self, parent,
        "Save changes? (yes, no, or cancel): ")
    self.controller = app.cu_editor.InteractiveQuit(host,
        self.textBuffer)


class InteractiveSaveAs(LabeledLine):
  def __init__(self, parent, host):
    LabeledLine.__init__(self, parent, "save as: ")
    self.controller = app.cu_editor.InteractiveSaveAs(host,
        self.textBuffer)


class LineNumbers(StaticWindow):
  def __init__(self, parent, host):
    StaticWindow.__init__(self, parent)
    self.host = host

  def drawLineNumbers(self):
    maxy, maxx = self.cursorWindow.getmaxyx()
    textBuffer = self.host.textBuffer
    limit = min(maxy, len(textBuffer.lines)-textBuffer.scrollRow)
    for i in range(limit):
      self.addStr(i, 0,
          ' %5d  '%(textBuffer.scrollRow+i+1), self.color)
    for i in range(limit, maxy):
      self.addStr(i, 0, '       ', 0)
    if 1:
      cursorAt = textBuffer.cursorRow-textBuffer.scrollRow
      self.addStr(cursorAt, 1,
          '%5d'%(textBuffer.cursorRow+1), self.colorSelected)
    self.cursorWindow.refresh()

  def refresh(self):
    self.drawLineNumbers()


class LogWindow(StaticWindow):
  def __init__(self, parent):
    StaticWindow.__init__(self, parent)
    self.lines = app.log.getLines()
    self.refreshCounter = 0

  def refresh(self):
    self.refreshCounter += 1
    app.log.info(" "*20, self.refreshCounter, "- screen refresh -")
    maxy, maxx = self.cursorWindow.getmaxyx()
    self.writeLineRow = 0
    for i in self.lines[-maxy:]:
      self.writeLine(i);
    StaticWindow.refresh(self)


class MessageLine(StaticWindow):
  """The message line appears at the bottom of the screen. It shows
       messages to the user, such as error messages."""
  def __init__(self, parent, host):
    StaticWindow.__init__(self, parent)
    self.host = host
    self.renderedMessage = None

  def refresh(self):
    tb = self.host.textBuffer
    #maxy, maxx = self.cursorWindow.getmaxyx()
    if not tb or self.renderedMessage is tb.message:
      #self.writeLine('<no text buffer>', 0)
      return
    app.log.debug('update message line\n',self.renderedMessage, '\n',
      tb.message)
    self.renderedMessage = tb.message
    self.writeLineRow = 0
    if tb.message:
      self.writeLine(tb.message[0], tb.message[1])
    else:
      self.blank()
    self.cursorWindow.refresh()


class StatusLine(StaticWindow):
  """The status line appears at the bottom of the screen. It shows the current
  line and column the cursor is on."""
  def __init__(self, parent, host):
    StaticWindow.__init__(self, parent)
    self.host = host

  def refresh(self):
    maxy, maxx = self.cursorWindow.getmaxyx()
    if False and self.parent.zOrder[-1] is self:
      Window.refresh(self)
    else:
      tb = self.host.textBuffer
      statusLine = self.host.textBuffer.relativePath
      if tb.isDirty():
        statusLine += ' * '
      else:
        statusLine += ' . '
      # Percentages.
      rowPercentage = 0
      colPercentage = 0
      lineCount = len(tb.lines)
      if lineCount:
        rowPercentage = tb.cursorRow*100/lineCount
        if tb.cursorRow >= lineCount - 1:
           rowPercentage = 100
        charCount = len(tb.lines[tb.cursorRow])
        if (tb.cursorCol < charCount):
          colPercentage = tb.cursorCol*100/charCount
        else:
          colPercentage = 100
      # Format.
      rightSide = '%s | %s | %4d,%2d | %3d%%,%3d%%'%(
          tb.cursorGrammarName(),
          tb.selectionModeName(),
          tb.cursorRow+1, tb.cursorCol+1,
          rowPercentage,
          colPercentage)
      statusLine += ' '*(maxx-len(statusLine)-len(rightSide)) + rightSide
      self.addStr(0, 0, statusLine, self.color)
      self.cursorWindow.refresh()


class TopInfo(StaticWindow):
  def __init__(self, parent, host):
    StaticWindow.__init__(self, parent)
    self.host = host
    self.borrowedRows = 0
    self.lines = []
    self.mode = 2

  def onChange(self):
    if self.mode == 0:
      return
    tb = self.host.textBuffer
    lines = []
    if len(tb.lines):
      lineCursor = tb.scrollRow
      line = ""
      while len(line) == 0 and lineCursor > 0:
        line = tb.lines[lineCursor]
        lineCursor -= 1
      if len(line):
        indent = 0
        while line[indent] == ' ':
          indent += 1
        lineCursor += 1
        while lineCursor < len(tb.lines):
          line = tb.lines[lineCursor]
          if not len(line):
            continue
          z = 0
          while line[z] == ' ':
            z += 1
          if z > indent:
            indent = z
            lineCursor += 1
          else:
            break
        while indent and lineCursor > 0:
          line = tb.lines[lineCursor]
          if len(line):
            z = 0
            while line[z] == ' ':
              z += 1
            if z < indent:
              indent = z
              lines.append(line)
          lineCursor -= 1
    lines.append(self.host.textBuffer.fullPath)
    self.lines = lines
    infoRows = len(self.lines)
    if self.mode > 0:
      infoRows = self.mode
    if self.borrowedRows != infoRows:
      self.host.resizeTopBy(infoRows-self.borrowedRows)
      self.resizeTo(infoRows, self.cols)
      self.borrowedRows = infoRows

  def refresh(self):
    """Render the context information at the top of the window."""
    lines = self.lines
    lines.reverse()
    for i,line in enumerate(lines):
      self.addStr(i, 0, line+' '*(self.cols-len(line)), self.color)
    for i in range(len(lines), self.rows):
      self.addStr(i, 0, ' '*self.cols, self.color)
    self.cursorWindow.refresh()


class InputWindow(Window):
  """This is the main content window. Often the largest pane displayed."""
  def __init__(self, prg, rows, cols, top, left):
    assert(prg)
    Window.__init__(self, prg)
    self.prg = prg
    self.showHeader = False
    self.showFooter = True
    self.useInteractiveFind = True
    self.showLineNumbers = True
    self.showMessageLine = True
    self.showRightColumn = True
    self.showTopInfo = True
    self.color = curses.color_pair(0)
    self.colorSelected = curses.color_pair(app.prefs.selectedColor)
    self.controller = app.controller.MainController(self)
    self.controller.add(app.cu_editor.CuaPlusEdit(prg, self))
    if 1:
      self.headerLine = HeaderLine(self, self)
      self.headerLine.color = curses.color_pair(168)
      self.headerLine.colorSelected = curses.color_pair(47)
      self.headerLine.setParent(self, 0)
      if not self.showHeader:
        self.headerLine.hide()
    if 1:
      self.interactiveFind = InteractiveFind(self)
      self.interactiveFind.color = curses.color_pair(0)
      self.interactiveFind.colorSelected = curses.color_pair(87)
      self.interactiveFind.setParent(self, 0)
      self.interactiveFind.hide()
    if 1:
      self.interactiveGoto = InteractiveGoto(prg, self)
      self.interactiveGoto.color = curses.color_pair(0)
      self.interactiveGoto.colorSelected = curses.color_pair(87)
      self.interactiveGoto.setParent(self, 0)
      self.interactiveGoto.hide()
    if 1:
      self.interactiveOpen = InteractiveOpener(prg, self)
      self.interactiveOpen.color = curses.color_pair(0)
      self.interactiveOpen.colorSelected = curses.color_pair(87)
      self.interactiveOpen.setParent(self, 0)
      self.interactiveOpen.hide()
    if 1:
      self.interactiveQuit = InteractiveQuit(prg, self)
      self.interactiveQuit.color = curses.color_pair(0)
      self.interactiveQuit.colorSelected = curses.color_pair(87)
      self.interactiveQuit.setParent(self, 0)
      self.interactiveQuit.hide()
    if 1:
      self.interactiveSaveAs = InteractiveSaveAs(prg, self)
      self.interactiveSaveAs.color = curses.color_pair(0)
      self.interactiveSaveAs.colorSelected = curses.color_pair(87)
      self.interactiveSaveAs.setParent(self, 0)
      self.interactiveSaveAs.hide()
    if 1:
      self.topInfo = TopInfo(self, self)
      self.topInfo.color = curses.color_pair(168)
      self.topInfo.colorSelected = curses.color_pair(47)
      self.topInfo.setParent(self, 0)
      if not self.showTopInfo:
        self.topInfo.hide()
    if 1:
      self.statusLine = StatusLine(self, self)
      self.statusLine.color = curses.color_pair(168)
      self.statusLine.colorSelected = curses.color_pair(47)
      self.statusLine.setParent(self, 0)
      if not self.showFooter:
        self.statusLine.hide()
    if 1:
      self.leftColumn = LineNumbers(self, self)
      self.leftColumn.color = curses.color_pair(211)
      self.leftColumn.colorSelected = curses.color_pair(146)
      self.leftColumn.setParent(self, 0)
      if not self.showLineNumbers:
        self.leftColumn.hide()
    if 1:
      self.rightColumn = StaticWindow(self)
      self.rightColumn.name = 'Right'
      self.rightColumn.color = curses.color_pair(18)
      self.rightColumn.colorSelected = curses.color_pair(105)
      self.rightColumn.setParent(self, 0)
      if not self.showRightColumn:
        self.rightColumn.hide()
    if 1:
      self.messageLine = MessageLine(self, self)
      self.messageLine.color = curses.color_pair(3)
      self.messageLine.colorSelected = curses.color_pair(87)
      self.messageLine.setParent(self, 0)
      if not self.showMessageLine:
        self.messageLine.hide()

    if 1:
      if self.prg.cliFiles:
        path = self.prg.cliFiles[0]['path']
        self.setTextBuffer(
            app.buffer_manager.buffers.loadTextBuffer(path))
      elif self.prg.readStdin:
        self.setTextBuffer(app.buffer_manager.buffers.readStdin())
      else:
        self.setTextBuffer(app.buffer_manager.buffers.newTextBuffer())

  def reshape(self, rows, cols, top, left):
    """Change self and sub-windows to fit within the given rectangle."""
    app.log.detail('reshape', rows, cols, top, left)
    lineNumbersCols = 7
    bottomRows = 1  # Not including status line.

    if self.showHeader:
      self.headerLine.reshape(1, cols, top, left)
      rows -= 1
      top += 1
    if self.showTopInfo:
      self.topInfo.reshape(0, cols-lineNumbersCols, top,
          left+lineNumbersCols)
    self.interactiveOpen.reshape(1, cols, top+rows-1, left)
    self.interactiveQuit.reshape(1, cols, top+rows-1, left)
    self.interactiveSaveAs.reshape(1, cols, top+rows-1, left)
    if self.showMessageLine:
      self.messageLine.reshape(bottomRows, cols, top+rows-bottomRows, left)
    if self.useInteractiveFind:
      self.interactiveFind.reshape(bottomRows, cols,
          top+rows-bottomRows, left)
    if 1:
      self.interactiveGoto.reshape(bottomRows, cols, top+rows-bottomRows, left)
    if self.showFooter:
      self.statusLine.reshape(1, cols, top+rows-bottomRows-1, left)
      rows -= bottomRows+1
    if self.showLineNumbers:
      self.leftColumn.reshape(rows, lineNumbersCols, top, left)
      cols -= lineNumbersCols
      left += lineNumbersCols
    if self.showRightColumn:
      self.rightColumn.reshape(rows, 1, top, left+cols-1)
      cols -= 1
    Window.reshape(self, rows, cols, top, left)

    if 1:
      tb = self.textBuffer
      cursor = app.history.get(['files', tb.fullPath, 'cursor'], (0, 0))
      if not len(tb.lines):
        row = col = 0
      else:
        row = max(0, min(cursor[0], len(tb.lines)-1))
        col = max(0, min(cursor[1], len(tb.lines[row])))
      tb.selectText(row, col, 0, app.selectable.kSelectionNone)

  def resizeTopBy(self, rowDelta):
    Window.resizeTopBy(self, rowDelta)
    self.leftColumn.resizeTopBy(rowDelta)
    self.rightColumn.resizeTopBy(rowDelta)
    self.textBuffer.updateScrollPosition()

  def drawRightEdge(self):
    """Draw makers to indicate text extending past the right edge of the
    window."""
    maxy, maxx = self.cursorWindow.getmaxyx()
    limit = min(maxy, len(self.textBuffer.lines)-self.textBuffer.scrollRow)
    for i in range(limit):
      color = self.rightColumn.color
      if len(self.textBuffer.lines[
          i+self.textBuffer.scrollRow])-self.textBuffer.scrollCol > maxx:
        color = self.rightColumn.colorSelected
      self.rightColumn.addStr(i, 0, ' ', color)
    for i in range(limit, maxy):
      self.rightColumn.addStr(i, 0, ' ', self.leftColumn.color)
    self.rightColumn.cursorWindow.refresh()

  def focus(self):
    self.messageLine.show()
    Window.focus(self)

  def quitNow(self):
    self.prg.quitNow()

  def refresh(self):
    self.topInfo.onChange()
    Window.refresh(self)
    self.drawRightEdge()
    self.cursorWindow.refresh()

  def setTextBuffer(self, textBuffer):
    app.log.info('setTextBuffer')
    #self.headerLine.controller.setFileName(textBuffer.fullPath)
    textBuffer.lineLimitIndicator = 80
    self.controller.setTextBuffer(textBuffer)
    Window.setTextBuffer(self, textBuffer)
    self.textBuffer.debugRedo = self.prg.debugRedo

  def unfocus(self):
    self.statusLine.cursorWindow.addstr(0, 0, ".")
    self.statusLine.refresh()
    self.messageLine.hide()
    Window.unfocus(self)


class PaletteWindow(Window):
  """A window with example foreground and background text colors."""
  def __init__(self, prg):
    Window.__init__(self, prg)
    self.resizeTo(16, 16*5)
    self.moveTo(8, 8)
    self.controller = app.controller.MainController(self)
    self.controller.add(app.cu_editor.PaletteDialogController(
        prg, self))
    textBuffer = app.text_buffer.TextBuffer()
    self.controller.setTextBuffer(textBuffer)
    Window.setTextBuffer(self, textBuffer)

  def draw(self):
    width = 16
    rows = 16
    for i in range(width):
      for k in range(rows):
        self.addStr(k, i*5, ' %3d '%(i+k*width,), curses.color_pair(i+k*width))
    self.cursorWindow.refresh()

  def refresh(self):
    self.draw()

