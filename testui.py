import webview

if __name__ == '__main__':
    # This creates a simple window with just the text "UI Test"
    webview.create_window('UI Test', html='<h1>Testing the UI...</h1>')
    webview.start(debug=True)