class CompQuestion extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            attention_answers: [], 
            classNameWrong: "d-none", 
            classNameCorrect: "d-none", 
            input_value: ""
        },
        this.submitCheck = this.submitCheck.bind(this);
    }


    submitCheck = () => {
        let { attention_answers} = this.state
        let AttentionInput = this.state.input_value
        let correct_answer = this.props.data["CorrectAnswer"]
        let field_ID = this.props.data["OtreeID"]
        //attention_answers = AttentionInput
        attention_answers.push(AttentionInput)
        
        this.setState({
            attention_answers
        })
        
        // Submit answer back to props
        this.props.suppliedAnswer(field_ID, AttentionInput)
        
        console.log(correct_answer)
        console.log(AttentionInput)

        if (Array.isArray(correct_answer)) {
            if (correct_answer.includes(AttentionInput) && AttentionInput !== "" ) {
                document.getElementById(field_ID).value = attention_answers
                this.setState({
                    classNameWrong: "d-none",
                    classNameCorrect: "alert alert-success"
                })
                
                this.props.allCorrect(field_ID)
            } else {
                this.setState({
                    classNameWrong: "alert alert-danger",
                    classNameCorrect: "d-none"
                })
            }
            
        } else {
            if (AttentionInput == correct_answer && AttentionInput !== "" ) {
                document.getElementById(field_ID).value = attention_answers
                this.setState({
                    classNameWrong: "d-none",
                    classNameCorrect: "alert alert-success",
                })
                this.props.allCorrect(field_ID)
            } else {
                this.setState({
                    classNameWrong: "alert alert-danger",
                    classNameCorrect: "d-none"
                })

                const allInputs = document.querySelectorAll('input:not(.largerRadio)')
                for (let i = 0, l = allInputs.length; i < l; i++) {
                    allInputs[i].disabled = true
                }
                
                const allButtons = document.querySelectorAll('button')
                for (let i = 0, l = allButtons.length; i < l; i++) {
                    allButtons[i].disabled = true
                }
                
                const closeButtons = document.querySelectorAll('.closeBtn')
                for (let i = 0, l = allButtons.length; i < l; i++) {
                    allButtons[i].disabled = true
                }

                const compQuestSection = document.getElementById("compQ")
                compQuestSection.style.cursor = "not-allowed"
                
                setTimeout(function () {
                    for (let i = 0, l = allInputs.length; i < l; i++) {
                        allInputs[i].disabled = false
                    }
                    for (let i = 0, l = allButtons.length; i < l; i++) {
                        allButtons[i].disabled = false
                    }
                    for (let i = 0, l = closeButtons.length; i < l; i++) {
                        closeButtons[i].disabled = true
                    }
                    compQuestSection.style.cursor = "auto"
                }, js_vars.wait_time * 1000)

            }
        }

    }

    sync_input = (e) => {
        this.setState({ input_value: e.target.value })
    }

    render() {
        let QuestionText = this.props.data["QuestionText"]
        let WrongText = this.props.data["WrongText"]
        let CorrectText = this.props.data["CorrectText"]
        return (
            <div className="my-1 container px-2 py-1">
                <label className="mb-2">
                    {QuestionText}
                </label>
                <input id={this.props.data['OtreeID'] + 'input'} type="number" onChange={this.sync_input} className="form-control mb-2" step="0.01"></input>
                <button 
                    type="button" 
                    id = {this.props.data['OtreeID'] + 'btn'}
                    className="btn btn-primary" 
                    onClick={() => this.submitCheck()}>
                    Submit your answer
                </button>
                <br></br>
                <br></br>
                <div className={`${this.state.classNameWrong}`}>
                    {WrongText}
                </div>
                <div className={`${this.state.classNameCorrect}`}>
                    {CorrectText}
                </div>
            </div>
        )
    }
}

class CompQuestionMC extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            attention_answers: [], 
            classNameNo: "d-none", 
            classNameWrong: "d-none", 
            classNameCorrect: "d-none", 
            selectedOption: -999,
            timer: undefined,
        },
        this.submitCheck = this.submitCheck.bind(this);
        this.setTimer = this.setTimer.bind(this);
    }

    componentDidMount(){
        // Disable arrow key behavior
        $('input[type="radio"]').keydown(function(e)
        {
            var arrowKeys = [37, 38, 39, 40];
            if (arrowKeys.indexOf(e.which) !== -1)
            {
                $(this).blur();
                return false;
            }
        });
    }
    

    submitCheck = () => {
        let { attention_answers } = this.state
        let AttentionInput = this.state.selectedOption
        let correct_answer = this.props.data["CorrectAnswer"]
        let field_ID = this.props.data["OtreeID"]
        attention_answers.push(AttentionInput)

        this.setState({
            attention_answers
        })

        this.props.suppliedAnswer(field_ID, AttentionInput)

        if (AttentionInput == correct_answer) {

            document.getElementById(field_ID).value = attention_answers

            this.setState({
                classNameWrong: "d-none",
                classNameCorrect: "alert alert-success",
                classNameNo: "d-none",
            }, () => {
                this.props.allCorrect(field_ID)
            });
            
        
        } else if (AttentionInput != -999) {
            this.setState({
                classNameWrong: "alert alert-danger",
                classNameCorrect: "d-none",
                classNameNo: "d-none",
            })

            const allInputs = document.querySelectorAll('input:not(.largerRadio)')
            for (let i = 0, l = allInputs.length; i < l; i++) {
                allInputs[i].disabled = true
            }
            
            const allButtons = document.querySelectorAll('button')
            for (let i = 0, l = allButtons.length; i < l; i++) {
                allButtons[i].disabled = true
            }

            const closeButtons = document.querySelectorAll('.closeBtn')
            for (let i = 0, l = allButtons.length; i < l; i++) {
                allButtons[i].disabled = true
            }

            const compQuestSection = document.getElementById("compQ")
            compQuestSection.style.cursor = "not-allowed"
            
            setTimeout(function () {
                for (let i = 0, l = allInputs.length; i < l; i++) {
                    allInputs[i].disabled = false
                }
                for (let i = 0, l = allButtons.length; i < l; i++) {
                    allButtons[i].disabled = false
                }
                for (let i = 0, l = closeButtons.length; i < l; i++) {
                    closeButtons[i].disabled = true
                }
                compQuestSection.style.cursor = "auto"
            }, js_vars.wait_time * 1000)
            
        } else {
            this.setState({
                classNameWrong: "d-none",
                classNameCorrect: "d-none",
                classNameNo: "alert alert-danger",
            })
        }
    }

    radioChange = (e) => {
        this.setState({
            selectedOption: Number(e.target.value),
            classNameWrong: "d-none",
            classNameCorrect: "d-none",
            classNameNo: "d-none",
        }, this.setTimer(200))
    }

    setTimer = (time) => {
        let timer = this.state.timer
        
        if (timer) {
            clearTimeout(timer);
        }
        timer = setTimeout(() => { this.submitCheck(); }, time);
        this.setState({timer})
    }

    render() {
        let radioItems = []
        let field_ID = this.props.data["OtreeID"] + "_MC"
        let AttentionInput = this.state.selectedOption

       for (let i = 0; i < this.props.data["Options"].length; i++) {
           radioItems.push(
            <div className="form-check form-check-inline">
                <input key={i} className="form-check-input" type="radio" onChange={this.radioChange}
                    id={field_ID + "_" + i} name={field_ID} 
                    value={this.props.data["Options"][i][0]}
                    style={{marginRight: "10px"}}
                ></input>

                <label htmlFor={field_ID + "_" + i} className="form-check-label">
                    {this.props.data["Options"][i][1]}
                </label>
            </div>
               )
       }

        let WrongText = this.props.data["WrongText"]

        return (
            <div className="my-1 container px-2 py-1">
                <label>
                    {this.props.data["QuestionText"]}
                </label> <br></br>

                {radioItems} 
                <br></br>

                {/*
                    <button type="button" className="btn btn-primary mb-2" 
                    id={this.props.data['OtreeID'] + 'btn'} 
                    onClick={() => this.submitCheck()}
                    
                    >
                    Submit your answer
                    </button>
                */}
           
                <div className={this.state.classNameNo}>
                    Please answer the question above.
                </div>
                <div className={this.state.classNameWrong}>
                    {WrongText.slice(AttentionInput - 1, AttentionInput)}
                </div>
                <div className={this.state.classNameCorrect}>
                    {this.props.data["CorrectText"]}
                </div>
            </div>
        )
    }
}

class AttentionCheck extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            classNameWrong: "d-none", classNameCorrect: "d-none", input_value: ""
        },
        this.submitCheck = this.submitCheck.bind(this);
        this.disableInput = this.disableInput.bind(this);
    }

    componentDidMount () {
        if (this.props.stopEntry) {
            this.disableInput()
        }
    }

    submitCheck = () => {
        let input = document.getElementById(this.props.data['OtreeID'] + 'input').value
        input = input.toLowerCase()
        let correct_answer = this.props.data["CorrectAnswer"]
        let correctChars = 0
        let correct = false


        // Compute Jaccard Distance
        function jaccard_index(s1, s2) {
            const inVal = new Set(s1)
            const compVal = new Set(s2)

            // Get the intersection set
            let intersect = new Set([...s1].filter(i => s2.includes(i)));

            // Sizes of both the sets
            let size_s1 = inVal.size;
            let size_s2 = compVal.size;
            
            // Size of the intersection set
            let size_in = intersect.size;
            
            // Calculate the Jaccard index
            // using the formula
            let jaccard_in  = size_in / (size_s1 + size_s2 - size_in);
        
            // Return the Jaccard index
            return jaccard_in;
        }


        /*
        Previous attention comparison
        
        for (var i = 0; i < correct_answer.length; i++) {
            let tmp = correct_answer.charAt(i)

            let inInput = input.includes(tmp)
            if (inInput){
                correctChars += 1
            }
        }
        
        if (correctChars >= correct_answer.length * 0.8){
            correct = true;
        }

        */

        if (jaccard_index(input, correct_answer) >= 0.8 ) {
            correct = true
        }
    
        if (correct) {
            this.setState({
                classNameWrong: "d-none",
                classNameCorrect: "alert alert-success"
            })

            //this.props.allCorrect(field_ID)
        } else {
            this.setState({
                classNameWrong: "alert alert-danger",
                classNameCorrect: "d-none"
            })
        }

        this.disableInput()
        this.props.submitted(correct)
    }

    disableInput () {
        document.getElementById(this.props.data['OtreeID'] + 'input').disabled = true;
        document.getElementById(this.props.data['OtreeID'] + 'btn').disabled = true;
        document.getElementById(this.props.data['OtreeID'] + 'btn').classList.add("d-none");
    }

    render() {
        let QuestionText = this.props.data["QuestionText"]
        let WrongText = this.props.data["WrongText"]
        return (
            <>
                <label>
                    {QuestionText}
                </label>
                <input 
                    id={this.props.data['OtreeID'] + 'input'} 
                    className="form-control mb-2"
                    ></input>
                <div id={this.props.data['OtreeID'] + '_wrong'} className={`${this.state.classNameWrong}`}>
                    {WrongText}
                </div>
                <button 
                    type="button" 
                    className="btn btn-primary mb-2" 
                    id={this.props.data['OtreeID'] + 'btn'} 
                    onClick={() => this.submitCheck()}>
                        Submit your answer
                </button>
            </>
        )
    }
}
