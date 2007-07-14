class Rect {
    public var x : Float;
    public var y : Float;
    public var w : Float;
    public var h : Float;
    
    public var centerx(get_centerx,set_centerx) : Float;
    public var centery(get_centery,set_centery) : Float;
    public var top(get_top,set_top): Float;
    public var right(get_right,set_right): Float;
    public var bottom(get_bottom,set_bottom): Float;
    public var left(get_left,set_left): Float;
    
    public function new(x_:Float,y_:Float,w_:Float,h_:Float) {
        x = x_;
        y = y_;
        w = w_;
        h = h_;
    }
    
    public function colliderect(b:Rect) {
        var a = this;
        if (a.bottom < b.top) { return false; }
        if (a.left > b.right) { return false; }
        if (a.top > b.bottom) { return false; }
        if (a.right < b.left) { return false; }
        return true;
    }
        
    private function get_centerx() { return x+w/2; }
    private function set_centerx(v:Float) { x = v-w/2; return x+w/2; }
    private function get_centery() { return y+h/2; }
    private function set_centery(v:Float) { y = v-h/2; return y+h/2; }
    private function get_top() { return y; }
    private function set_top(v:Float) { y = v; return y; }
    private function get_right() { return x+w; }
    private function set_right(v:Float) { x = v-w; return x+w; }
    private function get_bottom() { return y+h; }
    private function set_bottom(v:Float) { y = v-h; return y+h; }
    private function get_left() { return x; }
    private function set_left(v:Float) { x = v; return x; }
}
     
        
        