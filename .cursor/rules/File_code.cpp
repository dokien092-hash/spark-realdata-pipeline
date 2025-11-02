void reduce(int p)
{
    int k, ad;
    char src, *dest;
    
    switch(p)
    {
        case 1: // S → if C then S else S
            dest = "iCtSeS";
            src = 'S';
            break;
        case 2: // S → if C then S
            dest = "iCtS";
            src = 'S';
            break;
        case 3: // C → b
            dest = "b";
            src = 'C';
            break;
        case 4: // S → a
            dest = "a";
            src = 'S';
            break;
        default:
            dest = "\0";
            src = '\0';
            break;
    }
    
    for (k = 0; k < strlen(dest); k++) {
        pop();
        popb();
    }
    pushb(src);
    
    switch(src) {
        case 'S': ad = 0; break;
        case 'C': ad = 1; break;
        default: ad = -1; break;
    }
    push(gotot[TOS()][ad]);
}